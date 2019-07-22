#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import multiprocessing


ADD_PATHS_TO_EXE=['lib', 'lib\\library.zip', 'lib\\butterflow', 'lib\\numpy\\core', 'lib\\ffmpeg', 'lib\\misc']
# ADDED_PATHS=False

def add_paths_to_exe():
    # global ADDED_PATHS
    # if ADDED_PATHS:
        # return

    if hasattr(sys, "frozen"):
        # print("Settting PATHs for executable:")
        
        executable_dir = os.path.dirname(sys.executable).replace('/', os.sep)
        os.environ['PATH'] = executable_dir
        for path in ADD_PATHS_TO_EXE:
            os.environ['PATH'] += os.pathsep+os.path.join(executable_dir, path)

        # print(os.environ['PATH'])
        # ADDED_PATHS=True

add_paths_to_exe()

from butterflow.cli import main

if __name__ == '__main__':
    multiprocessing.freeze_support()
    sys.exit(main())
