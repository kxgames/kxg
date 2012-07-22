from __future__ import division

import pygame
import multiprocessing

class Main (object):
    """ Manage whichever engine is currently active.  This involves both
    updating the current engine and handling transitions between engines. """

    # Game Loop {{{1

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

    # }}}1

class MultiplayerDebugger (object):
    """ Simultaneously plays any number of different game loops, by executing
    each loop in its own process.  This greatly facilitates the debugging and
    testing multiplayer games. """

    # Process Class {{{1
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

    # }}}1

    # Constructor {{{1

    def __init__(self):
        self.threads = []

    # Run Methods {{{1

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

class Engine (object):

    # Constructor {{{1

    def __init__(self, master):
        self.master = master
        self.stop_flag = False

    # Attributes {{{1

    def get_master(self):
        return self.master

    # }}}1

    # Loop Completion {{{1

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

    # Loop Methods {{{1

    def setup(self):
        raise NotImplementedError

    def update(self, time):
        raise NotImplementedError

    def teardown(self):
        raise NotImplementedError

    # }}}1

class CleanupEngine (Engine):

    # Constructor {{{1

    def __init__(self, master):
        Engine.__init__(self, master)

    # Loop Methods {{{1

    def setup(self):
        self.exit_program()

    # }}}1

class GameEngine (Engine):

    # Constructor {{{1

    def __init__(self, master, blueprint):
        Engine.__init__(self, master)
        self.blueprint = blueprint

        self.state = None
        self.state_changed = True

    # }}}1

    # Setup Methods {{{1

    def setup(self):

        self.state = self.blueprint.define_initial_state()

        self.setup_actors()
        self.setup_mailbox()

    def setup_actors(self):

        self.world = self.blueprint.create_world()
        self.referee = self.blueprint.create_referee()
        self.players = self.blueprint.create_players()

        self.actors = self.players + [self.referee]
        read_only_world = ReadOnlyWorld(self.world)

        for actor in self.actors:
            actor.set_world(read_only_world)

    def setup_mailbox(self):

        def setup_pipe(entity):
            pipes = Pipe()
            entity.set_pipe(pipes[0])
            return pipes[1]

        self.world_pipe = setup_pipe(self.world)
        self.referee_pipe = setup_pipe(self.referee)
        self.player_pipes = [ setup_pipe(player) for player in self.players ]

        self.speaking_pipes = [self.referee_pipe] + self.player_pipes
        self.listening_pipes = [self.world_pipe] + self.speaking_pipes

    # Update Methods {{{1

    def update(self, time):

        state, state_changed = self.check_state()

        if state_changed == True:
            self.reset_mailbox(state)
            self.reset_world(state)
            self.reset_actors(state)

        self.update_actors(state, time)
        self.update_mailbox(state, time)
        self.update_world(state, time)

        if state == self.blueprint.define_final_state():
            self.check_for_finish()

    def update_actors(self, state, time):

        for actor in self.actors:
            actor.dispatch()
            actor.update(state, time)

    def update_mailbox(self, state, time):

        for pipe, message in self.receive_requests():

            status = message.validate(self.world)
            response = message.response(status)

            if response is not None:
                pipe.send(response)

            if status == True:
                self.forward_request(message)

            if type(message) == self.transition_message:
                self.switch_states()

    def update_world(self, state, time):
        self.world.dispatch()
        self.world.update(state, time)

    def reset_world(self, state):
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

    # Teardown Methods {{{1

    def teardown(self):
        pass

    # }}}1

    # State Machine Methods {{{1

    def switch_states(self):
        self.state = self.blueprint.define_next_state(self.state)
        self.state_changed = True

    def check_state(self):
        state_changed = self.state_changed
        self.state_changed = False

        return self.state, state_changed

    # Message Handling Methods {{{1

    def receive_requests(self):

        requests = []

        for pipe in self.speaking_pipes:
            for message in pipe.receive():
                request = pipe, message
                requests.append(request)

        return requests

    def forward_request(self, message):

        for pipe in self.listening_pipes:
            pipe.send(message)

    # }}}1
    
class SinglePlayerGameEngine (GameEngine):
    pass

class MultiplayerClientGameEngine (GameEngine):
    pass

class MultiplayerServerGameEngine (GameEngine):
    pass

class GameBlueprint (object):

    # Constructor {{{1

    def __init__(self):

        self.initial_state = 'pregame'
        self.final_state = 'postgame'

        self.state_transitions = {
                'pregame' : 'game',
                'game' : 'postgame' }

    # Virtual Interface Methods {{{1

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

class GameActor (object):

    # Constructor {{{1

    def __init__(self):

        self.__world = None
        self.__pipe = None

        self.setup_methods = {
                'pregame' : self.setup_pregame,
                'game' : self.setup_game,
                'postgame' : self.setup_postgame }

        self.update_methods = {
                'pregame' : self.update_pregame,
                'game' : self.update_game,
                'postgame' : self.update_postgame }

    # Attributes and Operators {{{1

    def get_world(self):
        return self.__world

    def set_world(self, world):
        self.__world = world

    def set_pipe(self, pipe):
        self.__pipe = pipe

    # Virtual Interface {{{1

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

    # }}}1

    # Game Loop Methods {{{1

    def setup(self, state):
        self.setup_methods[state]()

    def update(self, state, time):
        self.update_methods[state](time)

    # Message Handling Methods {{{1

    def request(self, message):
        self.__pipe.send(message)

    def dispatch(self):
        self.__pipe.dispatch()

    def respond(self, flavor, callback):
        self.__pipe.register(flavor, callback)

    # }}}1

class GameToken (object):

    # Constructor {{{1

    def __init__(self):
        self._proxies = {}

    # Proxy Access Methods {{{1

    def get_proxy(self, name):

        # Create proxies on demand.

        if name not in self._proxies:
            classes = self.get_proxy_classes()
            proxy = classes.get(name, GameTokenProxy)(name, self)
            self._proxies[name] = proxy

        return self._proxies[name]

    @classmethod
    def get_proxy_classes(cls):
        return {}

    # }}}1

# Getter Method Decorators {{{1

def data_getter(method):
    method.data_getter = True
    return method

def token_getter(method):
    method.token_getter = True
    return method

def token_wrapper(wrapper):

    def real_decorator(method):
        method.token_wrapper = wrapper
        return method

    return real_decorator

# }}}1

class MetaTokenProxy (type):

    # Class Instantiation {{{1

    def __call__(cls, name, token):

        # Create the new proxy object.
        proxy = cls.__new__(cls)

        proxy._name = name
        proxy._token = token
        proxy._methods = {}

        for key in dir(token):
            member = getattr(token, key)

            # Look for annotated methods.

            data_getter = hasattr(member, 'data_getter')
            token_getter = hasattr(member, 'token_getter')
            token_wrapper = hasattr(member, 'token_wrapper')

            if not callable(member):
                continue

            # Check for improper use of decorators.

            if data_getter and token_getter:
                raise BadTokenAttribute('defined-twice')

            if token_wrapper and not token_getter:
                raise BadTokenAttribute('unused-wrapper')

            # Record the marked methods in the new class member.

            if data_getter:
                proxy._methods[key] = member

            if token_getter:
                wrapper = cls.wrap_token_getter(name, member)
                proxy._methods[key] = wrapper

        proxy.__init__()
        
        return proxy

    # Token Getter Wrappers {{{1

    @staticmethod
    def wrap_token_getter(name, member):

        if hasattr(member, 'token_wrapper'):

            token_wrapper = member.token_wrapper

            def decorator(*args, **kwargs):
                result = member(*args, **kwargs)
                return token_wrapper(result)

        else:

            def decorator(*args, **kwargs):
                result = member(*args, **kwargs)

                if isinstance(result, GameToken):
                    return result.get_proxy(name)

                elif isinstance(result, (list, tuple)):
                    proxies = [ token.get_proxy(name) for token in result ]
                    return tuple(proxies)

                elif isinstance(result, dict):
                    proxies = {
                            key : token.get_proxy(name)
                            for key, token in results }
                    return proxies

                else:
                    raise ProxyCastingError()

        return decorator

    # }}}1

class GameTokenProxy (object):

    # Metaclass Definition {{{1

    __metaclass__ = MetaTokenProxy

    # Attribute Access {{{1

    def __getattr__(self, name):
        return self._methods[name]

    # }}}1

class GameMessage (object):

    # Virtual Interface {{{1

    def validate(self):
        raise NotImplementedError

    def response(self, status):
        raise NotImplementedError

    # }}}1

class Pipe (object):

    # Comments {{{1

    # This should be in it's own module, along with the network pipe and
    # possibly some high-level messaging frameworks.  The frameworks are less
    # important to me now that the game engine is basically its own
    # super-specific mailbox framework.

    # Construction {{{1

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

    # }}}1

    # Subscription Methods {{{1

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

    # Locking Methods {{{1

    def lock(self):
        assert not self.locked
        self.locked = True

    def unlock(self):
        assert self.locked
        self.locked = False

    # Outgoing messages {{{1

    def send(self, message):
        assert not self.locked
        self.outgoing_queue.append(message)

    def deliver(self):
        assert not self.locked

    # Incoming Messages {{{1

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

    # }}}1

