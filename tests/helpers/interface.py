import sys

class TestInterface:

    def __init__(self, title, tests, critical=True):
        self.title = title
        self.critical = critical

        self.test = 0
        self.tests = tests

        self.format = '(%d/%d)'
        self.length = len(self.format % (tests, tests))

        self.padding = ' ' * (self.length + 1)
        self.backspace = '\b' * self.length

    def __enter__(self):
        sys.stdout.write(self.title + self.padding)
        return self

    def __exit__(self, type, value, traceback):
        exception = type or value or traceback
        incomplete = self.test != self.tests

        backspace = self.backspace
        interrupt = (type == KeyboardInterrupt)

        if interrupt:
            exception = False
            backspace += '\b\b'

        if exception:       prefix = '\033[91m'     # Red.
        elif incomplete:    prefix = '\033[93m'     # Yellow.
        else:               prefix = '\033[92m'     # Green.

        suffix = '\033[0m'
        newline = '  \n'

        status = self.format % (self.test, self.tests)

        sys.stdout.write(backspace + prefix + status + suffix + newline)
        sys.stdout.flush()

        return not self.critical or interrupt

    @staticmethod
    def report_success():
        print "All tests passed."

    def update(self):
        self.test += 1
        status = self.format % (self.test, self.tests)

        sys.stdout.write(self.backspace + status)
        sys.stdout.flush()

