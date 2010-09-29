# -*- coding: utf8 -*-

""" Pblog setup and manage """

import sys

from pblog.core import Pblog

def setup(**kwargs):

    Pblog.instance = Pblog(**kwargs)
    cmd_map = {
            "create": "create",
            "run": "run",
            }

    # Exec a command ?
    if len(sys.argv) > 1 and sys.argv[1] in cmd_map:
        getattr(Pblog.instance, cmd_map[sys.argv[1]])()
    else:
        Pblog.instance.run()
