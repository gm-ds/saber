#!/usr/bin/env python3

import sys

if __name__ == '__main__':
    from saber._internal.cli.main import main as _main
    sys.exit(_main())
