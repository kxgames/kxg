#!/usr/bin/env python3

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL)

import sys, pytest
pytest.main(['--cov', 'kxg'] + sys.argv[1:])
