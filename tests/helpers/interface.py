import sys

class TestInterface:

    def __init__(self, title, tests, critical=True):
        self.title = title
        self.critical = critical

        self.test = 1
        self.tests = tests

        self.format = '(%d/%d)'
        self.length = len(self.format % (tests, tests))

        self.padding = ' ' * (self.length + 1)
        self.backspace = '\b' * self.length

    def __enter__(self):
        sys.stdout.write(self.title + self.padding)
        return self

    def __exit__(self, exception, value, traceback):
        prefix = '\033[91m' if exception else '\033[92m'
        suffix = '\033[0m'

        status = self.format % (self.test - 1, self.tests)
        newline = '\n'

        sys.stdout.write(self.backspace + prefix + status + suffix + newline)
        sys.stdout.flush()

        return not self.critical 

    @staticmethod
    def report_success():
        print "All tests passed."

    def update(self):
        status = self.format % (self.test, self.tests)
        self.test += 1

        sys.stdout.write(self.backspace + status)
        sys.stdout.flush()

