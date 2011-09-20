from __future__ import division

import pygame.time
from messaging import Forum

class Loop:
    """ Manage whichever game engine is currently active.  This involves both
    updating the current engine and handling transitions between engines. """

    # Game Loop {{{1
    def play(self, frequency=50):
        clock = pygame.time.Clock()
        self.stop_flag = False

        # All subclasses need to define self.engine.
        self.engine.setup()

        while not self.finished():
            time = clock.tick(frequency) / 1000
            self.engine.update(time)

            if self.engine.finished():
                self.engine.teardown()
                self.engine = self.engine.successor()
                self.engine.setup()

        self.engine.teardown()

    def exit(self):
        self.stop_flag = True

    def finished(self):
        return self.stop_flag

    # }}}1

class Engine:
    """ Control everything happening in the game.  This is just an abstract
    base class providing methods for updating and switching engines. """

    # Constructor {{{1
    def __init__(self, loop):
        self.loop = loop
        self.stop_flag = False

    # Attributes {{{1
    def get_loop(self):
        return self.loop
    # }}}1

    # Loop Completion {{{1
    def exit_engine(self):
        """ Stop this engine from executing once the current update ends. """
        self.stop_flag = True

    def exit_loop(self):
        """ Exit the game once the current update ends. """
        self.loop.exit()

    def finished(self):
        """ Return true if this engine is done executing. """
        return self.stop_flag

    def successor(self):
        """ Create and return the engine that should be executed next. """
        return None

    # Loop Methods {{{1
    def setup(self):
        """ Setup the engine.  This is called exactly one time before the first
        update cycle. """
        raise NotImplementedError

    def update(self, time):
        """ Update the engine.  This is called once a frame for as long as the
        engine is running.  The only argument gives the elapsed time since the
        last update. """
        raise NotImplementedError

    def teardown(self):
        """ Tear down the engine.  This is called after the last update, but
        before the successor() method is called to get the next engine. """
        raise NotImplementedError

    # }}}1

class GameEngine(Engine):
    """ Play the game using the standard game loop.  This class assumes that
    the world, game, and tasks attributes are all defined in a subclass.  The
    tasks generate messages, which are passed through the forum to the game.
    The game is responsible for changing the game world. """

    # Constructor {{{1
    def __init__(self, loop):
        Engine.__init__(self, loop)

        self.forum = Forum()

        self.world = None
        self.game = None

        self.tasks = {}

    # Attributes {{{1
    def get_world(self):
        return self.world

    def get_game(self):
        return self.game

    def get_publisher(self):
        return self.forum.get_publisher()

    def get_subscriber(self):
        return self.forum.get_subscriber()

    def get_member(self):
        return self.forum.get_member()

    def get_task(self, name):
        return self.tasks[name]

    # }}}1

    # Loop Methods {{{1
    def setup(self):
        for task in self.tasks.values():
            task.setup()

        self.game.setup()
        self.forum.lock()

    def update(self, time):
        for task in self.tasks.values():
            task.update(time)

        self.forum.deliver()
        self.game.update(time)

    def teardown(self):
        for task in self.tasks.values():
            task.teardown()

        self.game.teardown()

    # }}}1

class Task:
    """ Controls a single aspect of an engine.  Classes that implement this
    interface can be easily integrated into the serial or parallel engines.
    That said, a class can be manually used in any engine without inheriting
    from this. """

    # Constructor {{{1
    def __init__(self, engine):
        self.engine = engine

    def get_engine(self):
        return self.engine

    # Abstract Methods {{{1
    def setup(self):
        """ Setup the task.  This is called after the engine owning the
        task has finished constructing all of its tasks. """
        raise NotImplementedError

    def update(self, time):
        """ Update the task.  This is called once a frame for as long as the
        engine owning the task is running. """
        raise NotImplementedError

    def teardown(self):
        """ Tear down the task.  This is called when the engine owning the
        task is shutting down. """
        raise NotImplementedError

    # }}}1

