# -*- coding: utf8 -*-

# Core module, providing the unique Pblog instance (via Pblog.instance)
# available from anywhere in the code.

import os
import hashlib
import sqlalchemy as sa
import sqlalchemy.orm as orm

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm.exc import NoResultFound

# This is the default config, each item can be overwrite
# as param of setup() from __init__.py
_defconfig = {
    "name": "Charlie blog",     # Identifier for the blog (must be unique on db)
    "host": "localhost",        # bind host (TODO any ?)
    "port": 8000,               # bind port
    "cookie_secret": os.urandom(32).encode("hex"), # used for secure cookie (must be static in production)
    "db": "sqlite:///pblog.db", # db url (as parsed by sqlalchemy : http://www.sqlalchemy.org/docs/core/engines.html)
    "debug": False,             # Turn on/off debug on tornado and sqlalchemy engine
    "template_path": "templates", # templates path (relative to cwd)
    "static_path": "static"       # static content path (relative to cwd)
    }



class Pblog(object):
    instance = None

    def __init__(self, **kwargs):

        # overwrite default config with items from kwargs
        for key, val in _defconfig.iteritems():
            if not hasattr(self, key):
                if key in kwargs:
                    val = kwargs[key]
                setattr(self, key, val)

    @property
    def engine(self):
        if not hasattr(self, "_engine"):
            self._engine = sa.create_engine(self.db, echo=self.debug)
        return self._engine

    @property
    def Session(self):
        if not hasattr(self, "_Session"):
            self._Session = orm.scoped_session(orm.sessionmaker(bind=self.engine))
        return self._Session

    @property
    def session(self):
        if not hasattr(self, "_session"):
            self._session = self.Session()
        return self._session

    def create(self):
        from pblog.models import Blog

        # Create shema ?
        try:
            self.session.query(Blog).all()
        except (OperationalError, ProgrammingError):
            self.session.rollback()

            from pblog.models import metadata

            metadata.create_all(self.engine)

        # Create blog on database ?
        try:
            self.session.query(Blog).filter(Blog.name==self.name).one()
        except NoResultFound:
            from pblog.models import PblogConf
            blog = Blog(name=self.name)
            blog.conf = PblogConf()
            blog.conf.password = hashlib.sha1("admin").hexdigest()
            self.session.add(blog)
            self.session.commit()

    # Return the current Blog instance
    @property
    def blog(self):
        if not hasattr(self, "_blog"):
            from pblog.models import Blog
            self._blog = Blog.query.\
                    filter(Blog.name==self.name).one()
        return self._blog

    # Run the server
    # TODO: multiprocessing
    def run(self):
        settings = {"login_url": "/login"}
        for key in ("template_path", "static_path", "cookie_secret", "debug"):
            settings[key] = getattr(self, key)

        import tornado.web
        import tornado.httpserver
        import tornado.ioloop
        import pblog.views as views
        import pblog.admin as admin

        url = tornado.web.url

        app = tornado.web.Application([
            url(r"/", views.Root, name="root"),
            url(r"/post/(.+)", views.View, name="view"),
            url(r"/tag/(.+)", views.ViewTag, name="view_tag"),
            url(r"/page/(.+)", views.ViewPage, name="view_page"),
            url(r"/archives/(?P<year>\d+)/(?P<month>\d+)", views.ViewArchive, name="view_archive"),
            url(r"/feed/(?P<feed_type>atom|rss2)", views.FeedPost, name="feed_posts"),
            url(r"/feed/tag/(?P<tag_name>.*)/(?P<feed_type>atom|rss2)", views.FeedTag, name="feed_tag"),
            url(r"/login", admin.Login, name="Login"),
            url(r"/admin/", admin.Admin, name="Admin"),
            url(r"/admin/posts/", admin.PostList, name="PostList"),
            url(r"/admin/posts/edit/(\d+)", admin.PostEdit, name="PostEdit"),
            url(r"/admin/comments/", admin.CommentList, name="CommentList"),
            url(r"/admin/pages/", admin.PageList, name="PageList"),
            url(r"/admin/pages/edit/(\d+)", admin.PageEdit, name="PageEdit"),
            url(r"/admin/media/", admin.MediaList, name="MediaList"),
            url(r"/admin/designs/", admin.DesignList, name="DesignList"),
            url(r"/admin/conf/", admin.ConfEdit, name="ConfEdit"),
            url(r"/admin/links/", admin.ManageLinks, name="ManageLinks"),
            ], **settings)

        srv = tornado.httpserver.HTTPServer(app)
        srv.bind(self.port, address=self.host)
        srv.start()
        tornado.ioloop.IOLoop.instance().start()
