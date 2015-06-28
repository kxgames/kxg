#!/usr/bin/env python3

import pyglet

class Loop:
    """
    Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages.
    """

    def __init__(self, initial_stage):
        self.stage = initial_stage

    def play(self, frames_per_sec=50):
        self.stage.set_loop(self)
        self.stage.on_enter_stage()

        pyglet.clock.schedule_interval(self.update, 1/frames_per_sec)
        pyglet.app.run()

    def update(self, dt):
        self.stage.on_update_stage(dt)

        if self.stage.is_finished():
            self.stage.on_exit_stage()
            self.stage = self.stage.get_successor()

            if self.stage:
                self.stage.set_loop(self)
                self.stage.on_enter_stage()
            else:
                self.exit()

    def exit(self):
        if self.stage:
            self.stage.on_exit_stage()

        pyglet.app.exit()


