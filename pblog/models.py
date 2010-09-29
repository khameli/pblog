# -*- coding: utf8 -*-

""" SQLAlchemy models for Pblog """

from datetime import datetime

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base

from pblog.utils import markdownize, LazyDict
from pblog.core import Pblog
import pblog.forms as forms

__all__ = ["Tag", "Blog", "Post", "Comment", "Page", "PblogConf"]

prefix = "pblog_"

Base = declarative_base()
metadata = Base.metadata


class Tag(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(50), nullable=False, unique=True)

    __tablename__ = prefix + "tags"
    __mapper_args__ = {"order_by": name}
    query = Pblog.instance.Session.query_property()

    @property
    def url_args(self):
        return ("view_tag", self.name)

    def __repr__(self):
        ret = u"<Tag(%s)>" % (self.name,)
        return ret.encode("utf8")

class Blog(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(50), nullable=False, unique=True)
    conf = Column(PickleType)

    __tablename__ = prefix + "blog"
    query = Pblog.instance.Session.query_property()

class Post(Base):
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(512), nullable=False)
    post_date = Column(DateTime)
    content = Column(UnicodeText, nullable=False)
    slug = Column(Unicode(512), nullable=False)
    published = Column(Boolean, nullable=False)
    bid = Column(Integer, ForeignKey(Blog.id), nullable=False)
    blog = relation(Blog, backref=backref("posts", order_by=post_date.desc()))
    comments_allowed = Column(Boolean, nullable=False)

    __tablename__ = prefix + "post"
    __mapper_args__ = {"order_by": post_date.desc()}
    query = Pblog.instance.Session.query_property()


    def __init__(self, *a, **kw):

        self.errors = LazyDict()

        for k in ("title", "content", "slug"):
            kw.setdefault(k, "")

        kw.setdefault("post_date", datetime.now())
        kw.setdefault("published", True)
        kw.setdefault("comments_allowed", True)
        self.bid = Pblog.instance.blog.id

        return super(Post, self).__init__(*a, **kw)

    @property
    def render(self):
        return markdownize(self.content)


    @property
    def url_args(self):
        return ("view", self.slug)

    def __repr__(self):
        ret = u"<Post(%s)>" % (self.title,)
        return ret.encode("utf8")

class Comment(Base):
    id = Column(Integer, primary_key=True)
    post_date = Column(DateTime)
    name = Column(Unicode(512), nullable=False)
    content = Column(UnicodeText, nullable=False)
    email = Column(Unicode(512))
    ip = Column(Unicode(46)) # INET6_ADDRSLEN
    pid = Column(Integer, ForeignKey(Post.id), nullable=False)
    bid = Column(Integer, ForeignKey(Blog.id), nullable=False)
    post = relation(Post, backref=backref("comments", order_by=post_date.desc()))
    blog = relation(Blog, backref=backref("comments", order_by=post_date.desc()))

    __tablename__ = prefix + "comment"
    __mapper_args__ = {"order_by": post_date.asc()}
    query = Pblog.instance.Session.query_property()

    def __init__(self, **kw):

        self.errors = LazyDict()

        for k in ("name", "content", "email"):
            kw.setdefault(k, "")

        kw.setdefault("post_date", datetime.now())
        self.bid = Pblog.instance.blog.id

        return super(Comment, self).__init__(**kw)

    @property
    def render(self):
        return markdownize(self.content)

    @property
    def url_args(self):
        return ("view", self.post.slug)

    def __repr__(self):
        ret = u"<Comment(%s, %s)>" % (self.name, self.ip,)
        return ret.encode("utf8")

class Page(Base):
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(512), nullable=False)
    slug = Column(Unicode(512), nullable=False)
    post_date = Column(DateTime)
    content = Column(UnicodeText, nullable=False)
    published = Column(Boolean, nullable=False)
    bid = Column(Integer, ForeignKey(Blog.id), nullable=False)
    blog = relation(Blog, backref=backref("pages", order_by=post_date.desc()))

    __tablename__ = prefix + "page"
    __mapper_args__ = {"order_by": post_date.desc()}
    query = Pblog.instance.Session.query_property()

    def __init__(self, *a, **kw):

        self.errors = LazyDict()

        for k in ("title", "slug", "content"):
            kw.setdefault(k, "")

        kw.setdefault("post_date", datetime.now())
        kw.setdefault("published", True)
        self.bid = Pblog.instance.blog.id

        return super(Page, self).__init__(*a, **kw)

    @property
    def render(self):
        return markdownize(self.content)

    def __repr__(self):
        return u"<Page (%d)>" % (self.id,)


table_tp = Table(prefix+"tp", metadata,
        Column("pid", Integer, ForeignKey(Post.id)),
        Column("tid", Integer, ForeignKey(Tag.id)))

Post.tags = relation(Tag, backref="posts", secondary=table_tp)

Post.comment_count = column_property(select([func.count()],
    Comment.__table__.c.pid == Post.__table__.c.id).\
            correlate(Post.__table__).as_scalar().label('comment_count'))

Tag.post_count = column_property(select([func.count()],
    and_(Post.__table__.c.id == table_tp.c.pid,
        Tag.__table__.c.id == table_tp.c.tid)).\
                correlate(Tag.__table__).as_scalar().label("post_count"))


class PblogConf(object):
    EMAIL_DISABLED, EMAIL_OPTIONAL, EMAIL_REQUIRED = range(3)
    form = forms.Form(
            forms.Password("password",
                class_="medium-form-input",
                description="Admin password",
            ),
            forms.Textbox("title",
                forms.notnull,
                class_="medium-form-input",
                description="Blog title",
                pre="Example: Foo bar's blog",
                ),
            forms.Textbox("media_url",
                forms.notnull,
                class_="medium-form-input",
                description="Media url",
                pre="Media url form serving static content",
                ),
            forms.Dropdown("lang",
                [("en_US", "English"), ("fr_FR", "French"), ("ja_JP", "Japan")],
                description="Website language",
                ),
            forms.Textbox("max_post",
                forms.notnull,
                forms.regexp("\d+", "Must be a digit"),
                class_="small-form-input",
                description="Max posts by page",
                ),
            forms.Textbox("max_feed",
                forms.notnull,
                forms.regexp("\d+", "Must be a digit"),
                class_="small-form-input",
                description="Max posts by feed",
                ),
            forms.Textbox("max_comment",
                forms.notnull,
                forms.regexp("\d+", "Must be a digit"),
                class_="small-form-input",
                description="Max comments by feed",
                ),
            forms.Dropdown("email",
                [(unicode(EMAIL_DISABLED), "Disabled"), (unicode(EMAIL_OPTIONAL), "Optional"), (unicode(EMAIL_REQUIRED), "Required")],
                description="Email",
                pre="Require email on comment",
                ),
            )
    def __init__(self):
        self.theme = "ouverta"
        self.max_post = 10
        self.max_feed = 10
        self.max_comment = 10
        self.links = []
        self.top_links = []
        self.lang = ""
        self.media_url = "/static/"
        self.title = Pblog.instance.name
        self.email = self.EMAIL_OPTIONAL
        self.password = ""

    def __eq__(self, other):
        return self.__dict__ == other.__dict__ if other else False


