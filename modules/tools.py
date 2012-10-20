inf = infinity = float('inf')

class Timer:

    def __init__(self, duration, *callbacks):
        self.duration = duration
        self.callbacks = list(callbacks)

        self.elapsed = 0
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
        if self.elapsed > self.duration:
            return

        self.elapsed += time

        if self.elapsed > self.duration:
            for callback in self.callbacks:
                callback()


