# -*- coding: utf8 -*-

""" Various utils, string manipulation ... """

import re
import unicodedata
import functools

from markdown import markdown

def markdownize(*a, **kw):
    """ Markdownize a string with default extensions and safe_mode On """

    # set default params for markdown
    kw.setdefault("extensions", ["codehilite", "tables"])
    kw.setdefault("safe_mode", "escape")

    return markdown(*a, **kw)


def slugify(title):
    """ Slugify (taken from django project)
        Transform a string in a nice url string """
    try:
        value = unicode(title, 'utf-8')
    except:
        value = title
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)


class LazyDict(dict):
    """ dict returning "" if missing key
        TOREMOVE: it must be a better way to do that """
    def __getitem__(self, name):
        if name in self:
            return super(LazyDict, self).__getitem__(name)
        else:
            return ""


def feed_content(method):
    """ Decorator for views returning xml content (rss/atom) """
    @functools.wraps(method)
    def wrapper(self, *a, **kw):
        tpl = "feed_%s.xml" % (kw.pop("feed_type"),)
        self.set_header("Content-Type", "application/xml; charset=utf-8")
        kwargs = method(self, *a, **kw)
        return self.render(tpl, **kwargs)
    return wrapper
