#!/usr/bin/env python3

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL)

# This breaks tests, but makes the tests easier to debug.  What to do?
#import kxg.errors
#kxg.errors.ApiUsageError.message_width = 63

import sys, os, re, shlex, pytest

args = shlex.split('-x --color=yes --cov=kxg --cov-report=html') + sys.argv[1:]
test_pattern = re.compile(r'\d{2}_test_.+\.py')
if not any(filter(test_pattern.match, args)):
    args += sorted(filter(test_pattern.match, os.listdir('.')))

pytest.main(args)
