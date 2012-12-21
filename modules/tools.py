inf = infinity = float('inf')

class Timer:

    def __init__(self, duration, *callbacks):
        self.duration = duration
        self.callbacks = list(callbacks)

        self.elapsed = 0
        self.expired = False
        self.paused = False

    def register(self, callback):
        self.callbacks.append(callback)

    def unregister(self, callback):
        self.callbacks.remove(callback)

    def pause(self):
        self.paused = True

    def unpause(self):
        self.pause = False

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

    def has_expired(self):
        return self.expired

