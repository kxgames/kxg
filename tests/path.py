# This is a hack to get all the game modules on the import path.

import os, sys, subprocess

command = 'git', 'rev-parse', '--show-toplevel'
stdout = subprocess.check_output(command)
repository = stdout.strip()
path = os.path.dirname(repository)
sys.path.insert(0, path)
