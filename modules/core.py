import pygame.time

class Loop:
    """ Manage whichever game engine is currently active.  This involves both
    updating the current engine and handling transitions between engines. """

    # Game Loop {{{1
    def play(self):
        clock = pygame.time.Clock()
        frequency = settings.game.clock_rate

        self.engine.setup()     # All subclasses need to define self.engine.
        self.finished = False

        while not self.finished:
            time = clock.tick(frequency) / 1000
            self.engine.update(time)

            if self.engine.finished():
                self.engine.teardown()
                self.engine = self.engine.next()
                self.engine.setup()

    def finish(self):
        self.finished = True
    # }}}1

class Engine:
    """ Control everything happening in the game.  This is just an abstract
    base class providing methods for updating and switching engines. """

    # Constructor {{{1
    def __init__(self, loop):
        self.loop = loop
        self.complete = False

    # Attributes {{{1
    def get_loop(self):
        return self.loop
    # }}}1

    # Loop Completion {{{1
    def finish(self):
        """ Stop this engine from executing once the current update ends. """
        self.complete = True

    def finished(self):
        """ Return true if this engine is done executing. """
        return self.complete

    def next(self):
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
        before the next() method is called to get the next engine. """
        raise NotImplementedError

    # }}}1

class SerialEngine(Engine):
    """ Provide a simple mechanism for executing a set of unrelated services.
    Subclasses are expected to create a dictionary of services called
    self.services.  Every service in that list will be properly handled. """

    # Constructor {{{1
    def __init__(self, loop):
        Engine.__init__(self, loop)
        self.services = {}

    # Attributes {{{1
    def get_service(self, name):
        return self.services[name]

    # }}}1

    # Loop Methods {{{1
    def setup(self):
        for service in self.services.values():
            service.setup()

    def update(self, time):
        for services in self.services.values():
            service.update(time)

    def teardown(self):
        for services in self.services.values():
            service.teardown()

    # }}}1

class ParallelEngine(Engine):
    """ Provide a mechanism for executing game services in parallel.  This
    is still an abstract base class, but it allows subclasses to easily
    dispatch tasks into separate threads. """
    pass

class Service:
    """ Control a single aspect of an engine.  Classes that implement this
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
        """ Setup the service.  This is called after the engine owning the
        service has finished constructing all of its services. """
        raise NotImplementedError

    def update(self, time):
        """ Update the service.  This is called once a frame for as long as the
        engine owning the service is running. """
        raise NotImplementedError

    def teardown(self):
        """ Tear down the service.  This is called when the engine owning the
        service is shutting down. """
        raise NotImplementedError

    # }}}1

