inf = infinity = float('inf')

class Timer:

    def __init__(self, duration, *callbacks):
        self.duration = duration
        self.callbacks = list(callbacks)

        self.elapsed = 0
        self.expired = False
        self.paused = False

    def update(self, time):
        if self.expired:
            return

        if self.elapsed > self.duration:
            return

        self.elapsed += time

        if self.elapsed > self.duration:
            self.expired = True
            for callback in self.callbacks:
                callback()

    def restart(self):
        self.expired = False
        self.elapsed = 0

    def pause(self):
        self.paused = True

    def unpause(self):
        self.pause = False

    def register(self, callback):
        self.callbacks.append(callback)

    def unregister(self, callback):
        self.callbacks.remove(callback)

    def has_expired(self):
        return self.expired



def echo(*args, **kwargs):
    print args, kwargs or ''


