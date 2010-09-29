#!/usr/bin/env python

import os

args = {
        "name": "pblog",
        "version": "2.0",
        "description": "Python webblog",
        "long_description": "Pblog is a python webblog engine, using sqlalchemy and tornado plus markdown syntax",
        "author": "Philippe Pepiot & Julien Samama",
        "author_email": "phil@philpep.org, julien@philpep.org",
        "url": "https://projects.philpep.org/projects/pblog/",
        "packages": ["pblog"],
        }


try:
    from setuptools import setup
    args.update({ "install_requires": ["markdown", "tornado>=1.1", "sqlalchemy>=0.6"] })
except ImportError:
    from distutils.core import setup

data_files = []

def populate_datafiles(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        target = "share/pblog/%s" % (dirpath,)
        data_files.append([target, [os.path.join(dirpath, f) for f in filenames]])

for d in ("static", "templates"):
    populate_datafiles(d)

args.update({"data_files": data_files})

setup(**args)
