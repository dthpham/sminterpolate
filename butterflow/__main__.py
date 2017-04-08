#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import multiprocessing


if __name__ == '__main__':
    multiprocessing.freeze_support()

    import sys
    from butterflow.cli import main
    sys.exit(main())
