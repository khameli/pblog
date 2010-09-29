# -*- coding: utf8 -*-

import random
import hashlib

from tornado.web import authenticated
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.exc import NoResultFound

from pblog.views import BaseHandler
from pblog.models import *
from pblog.utils import LazyDict, slugify
from pblog.paginator import Paginator

__all__ = ["Login", "Admin", "PostList",
        "PostEdit", "CommentList",
        "PageList", "PageEdit", "MediaList",
        "DesignList", "ConfEdit", "ManageLinks"]

class AdminHandler(BaseHandler):

    def get_template_path(self):
        base = super(AdminHandler, self).get_template_path()
        return "%s/admin/" % (base,)

    def render(self, *a, **kw):
        kw.update({
            "conf": self.conf,
            "admin_url": self.conf.media_url+"admin",
            "theme_url": self.conf.media_url+self.conf.theme
            })
        return super(AdminHandler, self).render(*a, **kw)

class Login(AdminHandler):
    def get(self):
        if self.current_user == "admin":
            self.clear_cookie("user")
            self.redirect("/")
        return self.render("login.html")

    def post(self):
        password = self.get_argument("password", "")
        if self.conf.password != hashlib.sha1(password).hexdigest():
            return self.render("login.html")
        else:
            self.set_secure_cookie("user", "admin")
        self.redirect(self.get_argument("next", "/"))

class Admin(AdminHandler):
    @authenticated
    def get(self):
        last_comments = Comment.query.\
                filter(Comment.blog==self.blog).\
                order_by(Comment.post_date.desc()).limit(5)
        return self.render("index.html", last_comments=last_comments)

class PostList(AdminHandler):
    @authenticated
    def get(self):
        page = int(self.get_argument("p", 1))
        posts = Paginator(Post.query.\
                filter(Post.blog==self.blog).all(),
                self.conf.max_post).page(page)
        return self.render("posts.html", posts=posts)
    @authenticated
    def post(self):
        for i in self.request.arguments.iterkeys():
            post = Post.query.\
                    filter(Post.blog==self.blog).\
                    filter(Post.id==i).first()
            if post:
                self.orm.delete(post)
        self.commit()
        return self.get()

class PostEdit(AdminHandler):

    def get_post(self, post_id):

        post_id = int(post_id)

        if post_id == 0:
            return Post()
        else:
            try:
                post = Post.query.\
                        filter(Post.blog==self.blog).\
                        filter(Post.id==post_id).\
                        options(subqueryload(Post.tags)).one()
                post.errors = LazyDict()
                return post
            except NoResultFound:
                raise HTTPError(404)

    @authenticated
    def get(self, post_id):
        post = self.get_post(post_id)
        return self.render("edit.html", post=post)

    @authenticated
    def post(self, post_id):
        post = self.get_post(post_id)

        for k in ("title", "content", "slug"):
            setattr(post, k, self.get_argument(k, getattr(post, k)))
        for k in ("published", "comments_allowed"):
            setattr(post, k, bool(self.get_arguments(k, False)))

        for k in ("title", "content"):
            if not getattr(post, k):
                post.errors[k] = self.locale.translate("Cannot by empty")

        if not post.slug:
            post.slug = slugify(post.title)
            while Post.query.filter(Post.blog==self.blog).filter(Post.slug==post.slug).first():
                post.slug += unicode(random.randint(0, 9))

        if not post.errors:

            tags = self.get_argument("tags", "")

            if tags:
                tags = list(set([t for t in tags.split(",") if t]))
                current_tags = [t.name for t in post.tags]
                new_tags = [Tag.query.\
                        filter(Tag.name==t).first() \
                        or Tag(name=t) \
                        for t in tags if not t in current_tags]

                for t in new_tags:
                    post.tags.append(t)

                deleted_tags = [t for t in post.tags if not t.name in tags]
                for t in deleted_tags:
                    post.tags.remove(t)
                    if not t.posts:
                        self.orm.delete(t) # bye bye

            if not post.id:
                self.orm.add(post)
                self.commit()
                self.redirect(self.application.reverse_url("PostEdit", post.id))

            self.commit()

        return self.render("edit.html", post=post)


class CommentList(AdminHandler):
    @authenticated
    def get(self):
        page = int(self.get_argument("p", 1))
        comments = Paginator(Comment.query.\
                filter(Comment.blog==self.blog).\
                order_by(Comment.post_date.desc()).\
                options(subqueryload(Comment.post)),
                self.conf.max_comment).page(page)
        return self.render("comments.html", comments=comments)

class PageList(AdminHandler):
    @authenticated
    def get(self):
        page = int(self.get_argument("p", 1))
        pages = Paginator(Page.query.\
                filter(Page.blog==self.blog).all(),
                self.conf.max_post).page(page)
        return self.render("pages.html", pages=pages)
    @authenticated
    def post(self):
        for i in self.request.arguments.iterkeys():
            page = Page.query.\
                    filter(Page.blog==self.blog).\
                    filter(Page.id==i).first()
            if page:
                self.orm.delete(page)
        self.commit()
        return self.get()

class PageEdit(AdminHandler):

    def get_page(self, page_id):

        page_id = int(page_id)

        if page_id == 0:
            return Page()
        else:
            try:
                page = Page.query.\
                        filter(Page.blog==self.blog).\
                        filter(Page.id==page_id).one()
                page.errors = LazyDict()
                return page
            except NoResultFound:
                raise HTTPError(404)

    @authenticated
    def get(self, page_id):
        page = self.get_page(page_id)
        return self.render("edit_page.html", page=page)

    @authenticated
    def post(self, page_id):
        page = self.get_page(page_id)

        for k in ("title", "slug", "content"):
            setattr(page, k, self.get_argument(k, getattr(page, k)))

        setattr(page, "published", bool(self.\
                get_argument("published", False)))

        if not page.slug:
            page.slug = slugify(page.title)

            while Page.query.filter(Page.blog==self.blog).filter(Page.slug==page.slug).first():
                page.slug += unicode(random.randint(0, 9))

        for k in ("title", "content"):
            if not getattr(page, k):
                page.errors[k] = self.locale.translate("Cannot be empty")

        if not page.errors:

            if not page.id:
                self.orm.add(page)
                self.commit()
                self.redirect(self.application.reverse_url("PageEdit", page.id))

            self.commit()
        return self.render("edit_page.html", page=page)

class MediaList(AdminHandler):
    pass

class DesignList(AdminHandler):
    pass

class ConfEdit(AdminHandler):
    def get(self):
        form = self.conf.form()
        for f in form.inputs:
            if f.name != "password":
                f.value = unicode(getattr(self.conf, f.name))
        return self.render("conf.html", form=form)
    def post(self):
        form = self.conf.form()
        if form.validates(source=self.get_argument):
            for f in form.inputs:
                if f.name == "password" and f.value:
                    self.conf.password = hashlib.\
                            sha1(f.value).hexdigest()
                elif f.name != "password":
                    if isinstance(getattr(self.conf, f.name), int):
                        setattr(self.conf, f.name, int(f.value))
                    else:
                        setattr(self.conf, f.name, f.value)
            self.commit()
        return self.render("conf.html", form=form)


class ManageLinks(AdminHandler):
    pass
