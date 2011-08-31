# This is a hack to get all the game modules on the import path.  The first
# item in sys.path will always be the directory containing this script.  To add
# the game modules, I just need to move that path back one directory.

import os, sys

tests = sys.path[0]
repository = os.path.dirname(tests)
modules = os.path.join(repository, "modules")

sys.path.insert(0, modules)
