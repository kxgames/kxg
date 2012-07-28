from __future__ import division

import pygame

# Main (Game Loop) {{{1

class Main (object):
    """ Manage whichever engine is currently active.  This involves both
    updating the current engine and handling transitions between engines. """

    def play(self, frequency=50):

        try:
            clock = pygame.time.Clock()
            self.stop_flag = False

            # All subclasses need to define self.engine.
            self.engine.setup()

            while not self.is_finished():
                time = clock.tick(frequency) / 1000
                self.engine.update(time)

                if self.engine.is_finished():
                    self.engine.teardown()
                    self.engine = self.engine.get_successor()
                    self.engine.setup()

            self.engine.teardown()

        except KeyboardInterrupt:
            print

    def exit(self):
        self.stop_flag = True

    def is_finished(self):
        return self.stop_flag

# Multiplayer Debugger {{{1

class MultiplayerDebugger (object):
    """ Simultaneously plays any number of different game loops, by executing
    each loop in its own process.  This greatly facilitates the debugging and
    testing multiplayer games. """

    import multiprocessing

    # Process Class {{{2
    class Process(multiprocessing.Process):

        def __init__(self, name, loop):
            multiprocessing.Process.__init__(self, name=name)
            self.loop = loop

        def __nonzero__(self):
            return self.is_alive()

        def run(self):
            try: self.loop.play()
            except KeyboardInterrupt:
                pass

    # }}}2

    def __init__(self):
        self.threads = []

    def loop(self, name, loop):
        thread = MultiplayerDebugger.Process(name, loop)
        self.threads.append(thread)

    def run(self):
        try:
            for thread in self.threads:
                thread.start()

            for thread in self.threads:
                thread.join()

        except KeyboardInterrupt:
            pass

# }}}1
# Engine {{{1

class Engine (object):

    def __init__(self, master):
        self.master = master
        self.stop_flag = False

    def get_master(self):
        return self.master

    def exit_engine(self):
        """ Stop this engine from executing once the current update ends. """
        self.stop_flag = True

    def exit_program(self):
        """ Exit the game once the current update ends. """
        self.master.exit()

    def is_finished(self):
        """ Return true if this engine is done executing. """
        return self.stop_flag

    def get_successor(self):
        """ Create and return the engine that should be executed next. """
        return CleanupEngine(self.master)

    def setup(self):
        raise NotImplementedError

    def update(self, time):
        raise NotImplementedError

    def teardown(self):
        raise NotImplementedError

# Cleanup Engine {{{1

class CleanupEngine (Engine):

    def __init__(self, master):
        Engine.__init__(self, master)

    def setup(self):
        self.exit_program()

# }}}1
# Game Engine {{{1

class GameEngine (Engine):
    pass
    
# Game Blueprint {{{1

class GameBlueprint (object):

    def __init__(self):

        self.initial_state = 'pregame'
        self.final_state = 'postgame'

        self.state_transitions = {
                'pregame' : 'game',
                'game' : 'postgame' }

    def create_world(self):
        raise NotImplementedError

    def create_referee(self):
        raise NotImplementedError

    def create_players(self):
        raise NotImplementedError

    def define_referee_requests(self, state):
        raise NotImplementedError

    def define_player_requests(self, state):
        raise NotImplementedError

    def define_transition_message(self, state):
        raise NotImplementedError

    def define_quit_message(self, state):
        raise NotImplementedError

    def define_initial_state(self):
        return self.initial_state

    def define_final_state(self):
        return self.final_state

    def define_next_state(self, state):
        return self.state_transitions[state]

# }}}1
# Game Token Proxy Lock {{{1

class ProxyLock:

    def __init__(self, access, actor=None):
        self.current_access = access
        self.current_actor = actor

    def __enter__(self):
        self.previous_access = GameTokenProxy._access
        self.previous_actor = GameTokenProxy._actor

        GameTokenProxy._access = self.current_access
        GameTokenProxy._actor = self.current_actor

    def __exit__(self, *args, **kwargs):
        GameTokenProxy._access = self.previous_access
        GameTokenProxy._actor = self.previous_actor

    @staticmethod
    def restrict_default_access():
        GameTokenProxy._access = 'protected'

    @staticmethod
    def allow_default_access():
        GameTokenProxy._access = 'unprotected'

class ProtectedProxyLock (ProxyLock):
    def __init__(self, actor):
        ProxyLock.__init__(self, 'protected', actor.get_name())

class UnprotectedProxyLock (ProxyLock):
    def __init__(self):
        ProxyLock.__init__(self, 'unprotected', None)

# Single Player Game Engine {{{1

class SinglePlayerGameEngine (GameEngine):
    """ Manages running all of the game components on a single machine.  Right
    now the entire game engine is implemented in this class, but in the future
    I will move any code that is general to the multiplayer engines into the
    base game engine class.  Also note that the current implementation uses
    pipes, which I think is overkill.  In the future pipes will only be used
    for the multiplayer engines. """

    # Constructor {{{2

    def __init__(self, master, blueprint):
        Engine.__init__(self, master)
        self.blueprint = blueprint

        self.state = None
        self.state_changed = True

    # }}}2

    # Setup Methods {{{2

    def setup(self):

        self.state = self.blueprint.define_initial_state()
        ProxyLock.restrict_default_access()

        self.setup_actors()
        self.setup_mailbox()

    def setup_actors(self):

        self.world = self.blueprint.create_world()
        self.referee = self.blueprint.create_referee()
        self.players = self.blueprint.create_players()

        self.actors = self.players + [self.referee]

        for actor in self.actors:
            actor.set_world(self.world)

    def setup_mailbox(self):

        def setup_pipe(entity):
            pipes = Pipe()
            entity.set_pipe(pipes[0])
            return pipes[1]

        self.referee_pipe = setup_pipe(self.referee)
        self.player_pipes = [ setup_pipe(player) for player in self.players ]
        self.all_pipes = [self.referee_pipe] + self.player_pipes

    # Update Methods {{{2

    def update(self, time):

        state, state_changed = self.check_state()

        if state_changed == True:
            self.reset_world(state)
            self.reset_mailbox(state)
            self.reset_actors(state)

        self.update_world(state, time)
        self.update_actors(state, time)
        self.update_mailbox(state, time)

        if state == self.blueprint.define_final_state():
            self.check_for_finish()

    def update_actors(self, state, time):


        for actor in self.actors:
            with ProtectedProxyLock(actor):
                actor.dispatch()
                actor.update(state, time)

    def update_mailbox(self, state, time):

        for pipe, message in self.receive_requests():

            world = self.world
            verified = message.check(world)

            if not verified:
                continue

            with UnprotectedProxyLock():
                message.execute(world)

            for actor in self.actors:
                with ProtectedProxyLock(actor):
                    message.notify(actor)

            if type(message) == self.transition_message:
                self.switch_states()

    def update_world(self, state, time):
        with UnprotectedProxyLock():
            self.world.update(state, time)

    def reset_world(self, state):
        with UnprotectedProxyLock():
            self.world.setup(state)

    def reset_actors(self, state):
        for actor in self.actors:
            actor.setup(state)

    def reset_mailbox(self, state):

        referee_requests = self.blueprint.define_referee_requests(state)
        player_requests = self.blueprint.define_player_requests(state)

        self.referee_pipe.reset()
        self.referee_pipe.listen(*referee_requests)

        for pipe in self.player_pipes:
            pipe.reset()
            pipe.listen(*player_requests)

        self.transition_message = \
                self.blueprint.define_transition_message(state)

    def check_for_finish(self):

        statuses = [
                actor.is_postgame_finished()
                for actor in self.actors ]

        if all(statuses):
            self.exit_engine()

    # Teardown Methods {{{2

    def teardown(self):
        pass

    # }}}2

    # State Machine Methods {{{2

    def switch_states(self):
        self.state = self.blueprint.define_next_state(self.state)
        self.state_changed = True

    def check_state(self):
        state_changed = self.state_changed
        self.state_changed = False

        return self.state, state_changed

    # Message Handling Methods {{{2

    def receive_requests(self):

        requests = []

        for pipe in self.all_pipes:
            for message in pipe.receive():
                request = pipe, message
                requests.append(request)

        return requests

    def broadcast_response(self, message):

        for pipe in self.all_pipes:
            pipe.send(message)
    # }}}2

# Multiplayer Client Game Engine {{{1

class MultiplayerClientGameEngine (GameEngine):
    pass

# Multiplayer Server Game Engine {{{1

class MultiplayerServerGameEngine (GameEngine):
    pass

# }}}1

# Game Actor {{{1

class GameActor (object):

    # Constructor {{{2

    def __init__(self):

        self._world = None
        self._pipe = None

        self.setup_methods = {
                'pregame' : self.setup_pregame,
                'game' : self.setup_game,
                'postgame' : self.setup_postgame }

        self.update_methods = {
                'pregame' : self.update_pregame,
                'game' : self.update_game,
                'postgame' : self.update_postgame }

    # Attributes and Operators {{{2

    def get_name(self):
        return 'actor'

    def get_world(self):
        return self._world

    def set_world(self, world):
        self._world = world

    def set_pipe(self, pipe):
        self._pipe = pipe

    # Virtual Interface {{{2

    def setup_pregame(self):
        raise NotImplementedError

    def setup_game(self):
        raise NotImplementedError

    def setup_postgame(self):
        raise NotImplementedError

    def update_pregame(self, time):
        raise NotImplementedError

    def update_game(self, time):
        raise NotImplementedError

    def update_postgame(self, time):
        raise NotImplementedError

    def is_postgame_finished(self):
        return True

    # }}}2

    # Game Loop Methods {{{2

    def setup(self, state):
        self.setup_methods[state]()

    def update(self, state, time):
        self.update_methods[state](time)

    # Message Handling Methods {{{2

    def request(self, message):
        self._pipe.send(message)

    def dispatch(self):
        self._pipe.dispatch()

    def respond(self, flavor, callback):
        self._pipe.register(flavor, callback)

    # }}}2

# Game Token {{{1

class GameToken (object):

    def __new__(cls, *args, **kwargs):

        token = object.__new__(cls, *args, **kwargs)
        token.__init__(*args, **kwargs)
        proxy = GameTokenProxy(token)

        return proxy

    def __extend__(self):
        return {}

def data_getter(method):
    method.data_getter = True
    return method

# Game Token Proxy {{{1

class GameTokenProxy (object):

    _access = 'unprotected'
    _actor = None

    def __init__(self, token):

        self._token = token
        self._extensions = {
                actor : extension_class(self)
                for actor, extension_class in token.__extend__().items() }

    def __getattr__(self, key):

        access = GameTokenProxy._access
        actor = GameTokenProxy._actor

        token = self._token
        extension = self._extensions.get(actor)

        if hasattr(token, key):
            member = getattr(token, key)

            if access == 'unprotected' or hasattr(member, 'data_getter'):
                return member
            else:
                raise TokenPermissionError(key)

        elif extension and hasattr(extension, key):
            return getattr(extension, key)

        else:
            raise AttributeError(key)

class TokenPermissionError (Exception):
    pass

# Game Token Extension {{{1

class GameTokenExtension (object):
    def __init__(self, token):
        pass

# Game Message {{{1

class GameMessage (object):

    def check(self, world):
        raise NotImplementedError

    def execute(self, world):
        raise NotImplementedError

    def notify(self, actor):
        raise NotImplementedError

# Game World {{{1

class GameWorld (GameToken):
    """ Everything in this class is duplicated in the GameActor class.  I
    should have a generic base class that implements the setup/update/teardown
    functionality.  Of course, I'll have to think about ways to generalize that
    scheme first.  But it might be a good feature to stick into the base Engine
    class.   I also would like a way to avoid multiple inheritance. """

    def __init__(self):
        GameToken.__init__(self)

        self.setup_methods = {
                'pregame' : self.setup_pregame,
                'game' : self.setup_game,
                'postgame' : self.setup_postgame }

        self.update_methods = {
                'pregame' : self.update_pregame,
                'game' : self.update_game,
                'postgame' : self.update_postgame }

    def setup(self, state):
        self.setup_methods[state]()

    def update(self, state, time):
        self.update_methods[state](time)

    def setup_pregame(self):
        raise NotImplementedError

    def setup_game(self):
        raise NotImplementedError

    def setup_postgame(self):
        raise NotImplementedError

    def update_pregame(self, time):
        raise NotImplementedError

    def update_game(self, time):
        raise NotImplementedError

    def update_postgame(self, time):
        raise NotImplementedError

# }}}1

# Pipe {{{1

class Pipe (object):

    # Comments {{{2

    # This should be in it's own module, along with the network pipe and
    # possibly some high-level messaging frameworks.  The frameworks are less
    # important to me now that the game engine is basically its own
    # super-specific mailbox framework.

    # Construction {{{2

    # This little bit of black magic is probably more confusing than it's
    # worth.  It makes the constructor appear to return two pipes that have
    # already been connected to each other.

    def __new__(pipe_cls):
        queues = [], []
        pipes = object.__new__(pipe_cls), object.__new__(pipe_cls)

        pipes[0].__init__(queues[0], queues[1])
        pipes[1].__init__(queues[1], queues[0])

        return pipes

    def __init__(self, incoming_queue, outgoing_queue):

        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

        self.filters = set()
        self.callbacks = dict()

        self.locked = False

    # }}}2

    # Subscription Methods {{{2

    def listen(self, *flavors):
        assert not self.locked
        self.filters.update(flavors)

    def register(self, flavor, callback):
        assert not self.locked
        self.callbacks[flavor] = callback

    def reset(self):
        assert not self.locked
        self.filters = set()
        self.callbacks = dict()

    # Locking Methods {{{2

    def lock(self):
        assert not self.locked
        self.locked = True

    def unlock(self):
        assert self.locked
        self.locked = False

    # Outgoing messages {{{2

    def send(self, message):
        assert not self.locked
        self.outgoing_queue.append(message)

    def deliver(self):
        assert not self.locked

    # Incoming Messages {{{2

    def receive(self):
        assert not self.locked

        messages = []

        while self.incoming_queue:
            message = self.incoming_queue.pop()
            messages.append(message)

            filter_disabled = (len(self.filters) == 0)
            message_expected = type(message) in self.filters

            assert filter_disabled or message_expected

        if messages:
            count = len(messages)

        return messages

    def dispatch(self):
        assert not self.locked

        for message in self.receive():
            flavor = type(message)
            callback = self.callbacks.get(flavor, lambda x: None)

            callback(message)

    # }}}2

# }}}1
