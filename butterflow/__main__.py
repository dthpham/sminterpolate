#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import multiprocessing

if hasattr(sys, "frozen"):
    exedir = os.path.dirname(sys.executable)
    os.environ['PATH'] = exedir
    paths = ['lib',
             'lib/library.zip',
             'lib/butterflow',
             'lib/numpy/core',
             'lib/ffmpeg',
             'lib/misc']
    for path in paths:
        os.environ['PATH'] += os.pathsep + os.path.join(exedir, path)

from butterflow.cli import main


if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
