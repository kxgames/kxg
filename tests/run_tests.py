#!/usr/bin/env python3

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL)

# This breaks tests, but makes the tests easier to debug.  What to do?
#import kxg.errors
#kxg.errors.ApiUsageError.message_width = 63

import sys, shlex, glob, pytest
args = shlex.split('-x --color=yes --cov=kxg --cov-report=html')
tests = sys.argv[1:] or sorted(glob.glob('test_*.py'))
pytest.main(args + tests)
