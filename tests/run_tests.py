#!/usr/bin/env python3

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

# Run pytest.  All command-lines options are forwarded to pytest.  If one or 
# more test scripts are specified, only those will be run (and they will be run 
# in the order specified).  If no tests are specified, they will all be run (in 
# alphabetical order, hence the numeric prefixes).

import sys, os, re, shlex, pytest

args = shlex.split('-x --color=yes --cov=kxg --cov-report=html') + sys.argv[1:]
test_pattern = re.compile(r'\d{2}_test_.+\.py')
if not any(filter(test_pattern.match, args)):
    args += sorted(filter(test_pattern.match, os.listdir('.')))

pytest.main(args)
