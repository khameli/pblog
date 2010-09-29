# -*- coding: utf8 -*-

import os
import re
import datetime

from tornado.web import RequestHandler
from sqlalchemy.orm import subqueryload

from pblog.core import Pblog
from pblog.models import *
from pblog.paginator import Paginator
from pblog.utils import feed_content

__all__ = ["Root", "View", "ViewTag", "ViewPage",
        "ViewArchive", "FeedPost", "FeedTag"]

class BaseHandler(RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user")

    @property
    def conf(self):
        if not hasattr(self, "_conf"):
            self._conf = Blog.query.\
                    filter(Blog.id==self.blog.id).\
                    one().conf
        return self._conf

    @property
    def orm(self):
        if not hasattr(self, "_orm"):
            self._orm = Pblog.instance.session
        return self._orm

    @property
    def blog(self):
        if not hasattr(self, "_blog"):
            self._blog = Pblog.instance.blog
        return self._blog

    def commit(self):
        try:
            self.orm.commit()
        except:
            self.orm.rollback()
            raise HTTPError(500)


class ViewHandler(BaseHandler):

    def render(self, *a, **kw):
        archives = [datetime.date(e.post_date.year, e.post_date.month, 1) for e in Post.query.all()]
        archives = [(v, archives.count(v)) for v in list(set(archives))]
        archives.sort(reverse=True)
        kw.update({
            "conf": self.conf,
            "theme_url": self.conf.media_url+self.conf.theme,
            "all_tags": Tag.query.all(),
            "archives": archives,
            })
        for k in ("EMAIL_DISABLED", "EMAIL_OPTIONAL", "EMAIL_REQUIRED"):
            kw.update({k: getattr(PblogConf, k)})
        return super(ViewHandler, self).render(*a, **kw)

    def get_template_path(self):
        base = super(ViewHandler, self).\
                get_template_path()
        return "%s/%s" % (base, self.conf.theme,)


class Root(ViewHandler):
    def get(self):
        page = int(self.get_argument("p", 1))
        posts = Paginator(Post.query.\
                filter(Post.blog==self.blog).\
                options(subqueryload(Post.tags)),
                self.conf.max_post).page(page)
        return self.render("list.html", posts=posts)

class View(ViewHandler):
    def get_post(self, slug):
        try:
            return Post.query.\
                    filter(Post.blog==self.blog).\
                    filter(Post.slug==slug).\
                    options(subqueryload(Post.tags)).\
                    options(subqueryload(Post.comments)).one()
        except NoResultFound:
            raise HTTPError(404)

    def get(self, slug):
        post = self.get_post(slug)
        new_comment = Comment()
        return self.render("post.html",
                post=post, new_comment=new_comment)

    def post(self, slug):
        """ Post a comment on the given post """

        post = self.get_post(slug)

        kwargs = {"post": post, "ip": self.request.remote_ip }

        for k in ("name", "email", "content"):
            kwargs.update({k: self.get_argument(k, "")})

        new_comment = Comment(**kwargs)

        for k in ("name", "content"):
            if not getattr(new_comment, k):
                new_comment.errors[k] = self.locale.translate("Cannot be empty")

        if not new_comment.email and self.conf.email == conf.EMAIL_REQUIRED:
            new_comment.errors["email"] = self.locale.translate("Cannot be empty")
        elif self.conf.email \
                and self.conf.email != conf.EMAIL_DISABLED \
                and not re.match(".+@.+", new_comment.email):
            new_comment.errors["email"] = self.locale.translate("Not a valid email address")

        if not new_comment.errors:
            self.session.add(new_comment)
            self.commit()
            new_comment = Comment()

        return self.render("post.html",
                post=post, new_comment=new_comment)


class ViewTag(ViewHandler):
    def get(self, tag):
        page = int(self.get_argument("p", 1))
        posts = Paginator(Post.query.\
                filter(Post.blog==self.blog).\
                filter(Post.tags.any(Tag.name==unicode(tag))).\
                options(subqueryload(Post.tags)),
                    self.conf.max_post).page(page)
        return self.render("list.html", posts=posts)

class ViewArchive(ViewHandler):
    def get(self, year, month):
        page = int(self.get_argument("p", 1))
        year = int(year)
        month = int(month)

        if month == 12:
            next_year = year+1
            next_month = 1
        else:
            next_year = year
            next_month = month+1

        from_date = datetime.date(year, month, 1)
        to_date = datetime.date(next_year, next_month, 1)
        posts = Paginator(Post.query.\
                filter(Post.blog==self.blog).\
                filter(Post.post_date > from_date).\
                filter(Post.post_date < to_date).\
                options(subqueryload(Post.tags)),
                self.conf.max_post).page(page)
        return self.render("list.html", posts=posts)

class FeedPost(ViewHandler):
    @feed_content
    def get(self):
        posts = Post.query.\
                filter(Post.blog==self.blog).\
                options(subqueryload(Post.tags)).\
                limit(self.conf.max_feed)
        return {"posts": posts}

class FeedTag(ViewHandler):
    @feed_content
    def get(self, tag_name):
        posts = Post.query.\
                filter(Pblog.blog==self.blog).\
                filter(Post.tags.any(Tag.name==unicode(tag_name))).\
                limit(self.conf.max_feed)
        return {"posts": posts}


class ViewPage(ViewHandler):
    def get(self, slug):
        try:
            page = Page.query.\
                    filter(Page.blog==self.blog).\
                    filter(Page.slug==slug).one()
        except NoResultFound:
            raise HTTPError(404)

        return self.render("page.html", page=page)


