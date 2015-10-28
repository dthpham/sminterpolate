#!/usr/bin/env python2
# console scripts entry point into butterflow

import sys

if __name__ == '__main__':
    from butterflow.cli import main
    sys.exit(main())
