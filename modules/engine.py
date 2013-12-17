from __future__ import division

import functools

# Things to Remember
# ==================
# 1. Need to use a message to create new tokens.

# Things to Improve
# =================
# 1. Redo the initial connection system.  A MultiplayerClientConnectionStage 
#    will be basically responsible for setting up the forum.  I can also give 
#    it the ability to display some sort of splash screen in the future, so the 
#    game can not appear to freeze if the network lags suddenly.
#
# 2. Expand the Publisher/subscriber system.  There needs to be a centralized 
#    manager that knows what kinds of Message classes exist and what kinds of 
#    handlers have been defined.  It's disconcerting to not know if a spelling 
#    mistake has been made.  To catalog the message classes, I can use a 
#    metaclass.  To catalog the handlers, I can use a decorator.
#
# 3. Add methods to the message class to immediately react to messages, and to 
#    undo rejected messages.  
#
# 4. Allow Messenger objects to be locked.  This will allow me to check that 
#    tokens aren't saving references to the messenger and using them in stupid 
#    places.
#
# 5. Messages that do more than one thing might need to interleave calls to 
#    execute() and notify().  Consider a CreatePlayer message, which might 
#    create both a player and a city.  The notify() method really needs to be 
#    called after the player is created, so that the GUI can be properly set up 
#    before the city is created.  As it is, the city is instantiated and 
#    setup before the gui knows about the player, which makes it difficult to 
#    smartly initialize the city.
#
#    I wonder if I could do this with 'yield' statements.  That could be cool.

class GameEngineError (Exception):

    def __init__(self):
        self.format_args = ()
        self.format_kwargs = {}

    def __str__(self):
        import sys, textwrap

        try:
            indent = '    '
            format_args = self.format_args
            format_kwargs = self.format_kwargs

            message = self.message.format(*format_args, **format_kwargs)
            message = textwrap.dedent(message)
            message = textwrap.fill(message,
                    initial_indent=indent, subsequent_indent=indent)

            if self.details:
                details = self.details.format(*format_args, **format_kwargs)
                details = details.replace(' \n', '\n')
                details = textwrap.dedent(details)
                details = '\n\n' + textwrap.fill(details, 
                        initial_indent=indent, subsequent_indent=indent)
            else:
                details = ''

            return '\n' + message + details

        except Exception as error:
            import traceback
            return "Error in exception class: %s" % error


    def format_arguments(self, *args, **kwargs):
        self.format_args = args
        self.format_kwargs = kwargs

    def raise_if(self, condition):
        if condition: raise self

    def raise_if_not(self, condition):
        if not condition: raise self

    def raise_if_warranted(self):
        raise NotImplementedError


class NullTokenIdError (GameEngineError):

    message = "Token {0} has a null id."
    details = """\
            This error usually means that a token was added to the world 
            without being assigned an id number.  To correct this, add a call 
            to give_id() in the setup() method of the message responsible for 
            creating the token in question.  The id_factory required by 
            give_id() is provided as the second argument to setup()."""

    def __init__(self, token):
        self.token = token
        self.format_arguments(token)

    def raise_if_warranted(self):
        if self.token.get_id() is None:
            raise self


class UnexpectedTokenIdError (GameEngineError):

    message = "Token {0} already has an id."
    details = "This error usually means that {0} was added to the world twice."

    def __init__(self, token):
        self.token = token
        self.format_arguments(token)

    def raise_if_warranted(self):
        if self.token.get_id() is not None:
            raise self


class UnknownTokenStatus (GameEngineError):

    message = "Token has unknown status '{0}'."

    def __init__(self, token):
        self.status = token._status
        self.format_arguments(self.status)

    def raise_if_warranted(self):
        known_statuses = (
                Token._before_setup,
                Token._register,
                Token._after_teardown)

        if self.status not in self.known_statuses:
            raise self



class Loop (object):

    def update(self, time):
        self.stage.update(time)

        if self.stage.is_finished():
            self.stage.teardown()
            self.stage = self.stage.get_successor()

            if self.stage:
                self.stage.set_master(self)
                self.stage.setup()
            else:
                self.exit()

    def exit(self):
        raise NotImplementedError

    def get_initial_stage(self):
        raise NotImplementedError


class PygameLoop (Loop):
    """ Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages. """

    def play(self, frames_per_sec=50):
        import pygame

        try:
            clock = pygame.time.Clock()
            self.stop_flag = False

            self.stage = self.get_initial_stage()
            self.stage.set_master(self)
            self.stage.setup()

            while not self.is_finished():
                time = clock.tick(frames_per_sec) / 1000
                self.update(time)

            if self.stage:
                self.stage.teardown()

        except KeyboardInterrupt:
            print

    def exit(self):
        self.stop_flag = True

    def is_finished(self):
        return self.stop_flag


class PygletLoop (Loop):

    def play(self, frames_per_sec=50):
        import pyglet

        self.window = pyglet.window.Window()

        self.stage = self.get_initial_stage()
        self.stage.set_master(self)
        self.stage.setup()

        pyglet.clock.schedule_interval(self.update, 1/frames_per_sec)
        pyglet.app.run()

    def exit(self):
        import pyglet
        if self.stage: self.stage.teardown()
        pyglet.app.exit()

    def get_window(self):
        return self.window


class MultiplayerDebugger (object):
    """ Simultaneously plays any number of different game loops, by executing
    each loop in its own process.  This greatly facilitates the debugging and
    testing multiplayer games. """

    import multiprocessing

    class Process(multiprocessing.Process):

        def __init__(self, name, loop):
            MultiplayerDebugger.multiprocessing.Process.__init__(self, name=name)
            self.loop = loop
            self.logger = MultiplayerDebugger.Logger(name)

        def __nonzero__(self):
            return self.is_alive()

        def run(self):
            try:
                with self.logger:
                    self.loop.play(50)
            except KeyboardInterrupt:
                pass

    class Logger:

        def __init__(self, name, use_file=False):
            self.name = name.lower()
            self.header = '%6s: ' % name
            self.path = '%s.log' % self.name
            self.use_file = use_file
            self.last_char = '\n'

        def __enter__(self):
            import sys
            sys.stdout, self.stdout = self, sys.stdout
            if self.use_file: self.file = open(self.path, 'w')

        def __exit__(self, *ignored_args):
            import sys
            sys.stdout = self.stdout
            if self.use_file: self.file.close()

        def write(self, line):
            annotated_line = ''

            if self.last_char == '\n':
                annotated_line += self.header

            annotated_line += line[:-1].replace('\n', '\n' + self.header)
            annotated_line += line[-1]

            self.last_char = line[-1]

            self.stdout.write(annotated_line)
            if self.use_file: self.file.write(line)

        def flush(self):
            pass


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



class Publisher (object):

    def __init__(self, *subscribers):
        self.subscribers = list(subscribers)

    def register(self, subscriber):
        self.subscribers.append(subscriber)

    def unregister(self, subscriber):
        self.subscribers.remove(subscriber)

    def publish(self, type, *args, **kwargs):
        for subscriber in self.subscribers:
            subscriber.receive(type, *args, **kwargs)


class Subscriber (object):

    def receive(self, type, *args, **kwargs):
        raise NotImplementedError


class NullSubscriber (Subscriber):

    def receive(self, type, *args, **kwargs):
        pass


class CallbackSubscriber (Subscriber):

    def __init__(self, callback):
        self.callback = callback

    def receive(self, type, *args, **kwargs):
        self.callback(type, *args, **kwargs)


class InspectionBasedSubscriber (Subscriber):

    def __init__(self, delegate, template='{0}'):
        self.template = template
        self.delegate = delegate
        self.complain_by_default()

    def receive(self, type, *args, **kwargs):
        try:
            handler = getattr(self.delegate, self.template.format(type))
        except AttributeError:
            self.default(type, *args, **kwargs)
        else:
            handler(*args, **kwargs)

    def set_delegate(self, delegate):
        self.delegate = delegate

    def set_template(self, template):
        self.template = template

    def set_default(self, handler):
        self.default = callback

    def ignore_by_default(self):
        self.default = lambda *args, **kwargs: None

    def complain_by_default(self):
        def handle_with_complaint(type, *args, **kwargs):
            data = self.delegate, self.template.format(type)
            raise AssertionError("Expected %s to provide %s()." % data)
        self.default = handle_with_complaint



class Stage (object):

    def __init__(self):
        self._stop_flag = False

    def get_master(self):
        return self._master

    def set_master(self, master):
        self._master = master

    def exit_stage(self):
        """ Stop this stage from executing once the current update ends. """
        self._stop_flag = True

    def exit_program(self):
        """ Exit the game once the current update ends. """
        self._master.exit()

    def is_finished(self):
        """ Return true if this stage is done executing. """
        return self._stop_flag

    def get_successor(self):
        """ Create and return the stage that should be executed next. """
        return None

    def setup(self):
        raise NotImplementedError

    def update(self, time):
        raise NotImplementedError

    def teardown(self):
        raise NotImplementedError


class GameStage (Stage):

    def __init__(self, world, forum, actors):
        Stage.__init__(self)
        self.world = world
        self.forum = forum
        self.actors = actors
        self.successor = None

    def setup(self):
        """ Prepares the actors, world, and messaging system to begin playing
        the game.  This function is only called once, and is therefore useful
        for initialization code. """

        # Setup the forum first.  Note that on clients, this blocks until an 
        # id number is received from the forum running on the server.

        self.forum.setup(self.world, self.actors)

        # Setup the world before setting up the actors, so that the actors can 
        # feel free to read information out of the world when building 
        # themselves.

        self.world.define_actors(self.actors)
        self.world._status = Token._registered

        with UnrestrictedTokenAccess():
            self.world.setup()

        for actor in self.actors:
            print actor
            actor.setup(self.world)

    def update(self, time):
        """ Sequentially updates the actors, world, and messaging system.  The
        loop terminates once all of the actors indicate that they are done. """

        still_playing = False

        for actor in self.actors:
            actor.update(time)
            if not actor.is_finished(self.world):
                still_playing = True

        if not still_playing:
            self.exit_stage()

        self.forum.update()

        with UnrestrictedTokenAccess():
            self.world.update(time)

    def teardown(self):
        self.forum.teardown()

        for actor in self.actors:
            actor.teardown()

        with UnrestrictedTokenAccess():
            self.world.teardown()

    def get_successor(self):
        return self.successor

    def set_successor(self, successor):
        self.successor = successor


class SinglePlayerGameStage (GameStage):

    def __init__(self, world, referee, remaining_actors):
        forum = Forum()
        actors = [referee]

        if isinstance(remaining_actors, dict):
            for actor, greeting in remaining_actors.items():
                actor.send_message(greeting)
                actors.append(actor)
        else:
            actors.extend(remaining_actors)

        GameStage.__init__(self, world, forum, actors)


class MultiplayerClientGameStage (Stage):

    def __init__(self, world, actor, pipe):
        Stage.__init__(self)

        self.world = world
        self.actor = actor
        self.forum = ClientForum(pipe)

    def setup(self):
        pass

    def update(self, time):
        if self.forum.connect():
            self.exit_stage()

    def teardown(self):
        pass

    def get_successor(self):
        return GameStage(self.world, self.forum, [self.actor])


class MultiplayerServerGameStage (GameStage):

    def __init__(self, world, referee, pipes):
        forum = Forum()
        actors = [referee]

        if isinstance(pipes, dict):
            for pipe, greeting in pipes.items():
                actor = RemoteActor(pipe)
                actor.send_message(greeting)
                actors.append(actor)
        else:
            actors += [RemoteActor(pipe) for pipe in pipes]

        GameStage.__init__(self, world, forum, actors)



class Actor (object):

    def __init__(self):
        self.id = None
        self.messenger = Messenger(self)

    def get_id(self):
        assert self.id is not None, "Actor does not have id."
        return self.id

    def give_id(self, id):
        assert self.id is None, "Actor already has id."
        self.id = id

    def get_messenger(self):
        return self.messenger

    def is_finished(self, world):
        return world.has_game_ended()


    def setup(self, world):
        pass

    def update(self, time):
        pass

    def teardown(self):
        pass


    def send_message(self, message):
        self.messenger.send_message(message)

    def accept_message(self, message, verified):
        message.accept(self, verified)

    def reject_message(self, message):
        message.reject(self)

    def handle_message(self, message):
        message.notify(self, message.was_sent_from_here())

    def dispatch_message(self, message):
        pass


class RemoteActor (Actor):

    def __init__(self, pipe):
        Actor.__init__(self)

        self.pipe = pipe
        self.pipe.lock()

    def give_id(self, id):
        Actor.give_id(self, id)
        message = IdMessage(id)
        self.pipe.send(message)

    def is_finished(self, world):
        return self.pipe.finished() or Actor.is_finished(self, world)


    def setup(self, world):
        serializer = TokenSerializer(world)
        self.pipe.push_serializer(serializer)

    def update(self, time):
        self.pipe.deliver()
        for message in self.pipe.receive():
            self.messenger.send_message(message)

    def teardown(self):
        self.pipe.pop_serializer()


    def accept_message(self, message, verified):
        pass

    def reject_message(self, message):
        message.set_origin(True)
        self.pipe.send(message)

    def handle_message(self, message):
        pass

    def dispatch_message(self, message):
        self.pipe.send(message)


class Referee (Actor):

    def __init__(self):
        Actor.__init__(self)

    def setup(self, world):
        self.world = world

    def update(self, time):
        for token in self.world:
            token.report(self.messenger)


class Forum (object):

    def setup(self, world, actors):
        self.world = world
        self.actors = actors
        self.id_factory = IdFactory(world)

        for id, actor in enumerate(actors):
            actor.give_id(id)

    def update(self):
        world = self.world

        for sender in self.actors:
            sender_id = sender.get_id()
            messenger = sender.get_messenger()

            for message in messenger.deliver_messages():
                type = message.type()
                status = message.check(world, sender_id)
                message.set_status(status)

                if message.was_accepted():
                    sender.accept_message(message, True)
                else:
                    sender.reject_message(message)
                    continue

                with UnrestrictedTokenAccess():
                    message.setup(world, self.id_factory)

                for actor in self.actors:
                    private_message = message.copy()
                    private_message.set_origin(actor is sender)
                    actor.dispatch_message(private_message)

                with UnrestrictedTokenAccess():
                    world.handle_message(message)

                for actor in self.actors:
                    private_message = message.copy()
                    private_message.set_origin(actor is sender)
                    actor.handle_message(private_message)

    def teardown(self):
        pass


class ClientForum (object):

    def __init__(self, pipe):
        self.actor_id = None
        self.pipe = pipe
        self.pipe.lock()

    def connect(self):
        for message in self.pipe.receive():
            if isinstance(message, IdMessage):
                self.actor_id = message.id
                return True
        return False

    def setup(self, world, actors):
        assert len(actors) == 1

        self.world = world
        self.messages = []

        self.actor = actors[0]
        self.actor.give_id(self.actor_id)

        serializer = TokenSerializer(world)
        self.pipe.push_serializer(serializer)

    def update(self):
        world = self.world
        actor, actor_id = self.actor, self.actor.get_id()
        messenger = actor.get_messenger()

        # Send messages.
        for message in messenger.deliver_messages():
            status = message.check(world, actor_id)

            if status:
                actor.accept_message(message, False)
            else:
                actor.reject_message(message)
                continue

            self.pipe.send(message)

        self.pipe.deliver()

        # Receive messages.
        for message in self.pipe.receive():
            if message.was_sent_from_here():
                if message.was_accepted():
                    actor.accept_message(message, True)
                else:
                    actor.reject_message(message)
                    continue

            with UnrestrictedTokenAccess():
                world.handle_message(message)

            actor.handle_message(message)

    def teardown(self):
        self.pipe.pop_serializer()


class Messenger (object):

    def __init__(self, actor):
        self.actor = actor
        self.messages = []

    def send_message(self, message):
        self.messages.append(message)

    def deliver_messages(self):
        buffer = self.messages; self.messages = []
        return buffer
    

class IdFactory (object):

    def __init__(self, world):
        self.next_id = world.get_id() + 1

    def next(self):
        result = self.next_id
        self.next_id += 1
        return result



def read_only(method):
    return TokenMetaclass.read_only(method)

def before_setup(method):
    return TokenMetaclass.before_setup(method)

def after_teardown(method):
    return TokenMetaclass.after_teardown(method)

def check_for_prototype(method):
    @functools.wraps(method)
    def decorator(self, *args, **kwargs):
        self.check_for_prototype()
        return method(self, *args, **kwargs)
    return decorator

def check_for_instance(method):
    @functools.wraps(method)
    def decorator(self, *args, **kwargs):
        self.check_for_instance()
        return method(self, *args, **kwargs)
    return decorator


class TokenMetaclass (type):

    read_only_flag = '__read_only__'
    before_setup_flag = '__before_setup__'
    after_teardown_flag = '__after_teardown__'

    read_only_special_cases = '__str__', '__repr__'
    before_setup_special_cases = '__init__', '__extend__'

    class TokenSetupError (GameEngineError):

        message = "May have forgotten to add {0} to the world."
        details = """\
                The {0}.{1}() method was invoked on a token that had not yet 
                been added to the game world.  This is usually a sign that the 
                token in question was never added to the game world.  Label the 
                {1}() method with the kxg.before_setup decorator if you do 
                need it to setup {0} tokens."""

        def __init__(self, token, method):
            class_name = token.__class__.__name__
            method_name = method.__name__

            self.method = method
            self.format_arguments(class_name, method_name)

        def raise_if_warranted(self):
            if not hasattr(self.method, TokenMetaclass.before_setup_flag):
                raise self

    class TokenAccessError (GameEngineError):

        message = "Attempted unsafe invocation of {0}.{1}()."
        details = """\
                This error is meant to bring attention to situations that might 
                cause synchronization issues in multiplayer games.  The {1}() 
                method is not marked as read-only, but it was invoked from 
                outside the context of a message.  This means that if {1}() 
                makes any changes to the world, those changes will not be 
                propagated. If {1}() is actually read-only, mark it with the 
                @kxg.read_only decorator."""

        def __init__(self, token, method):
            class_name = token.__class__.__name__
            method_name = method.__name__

            self.method = method
            self.format_arguments(class_name, method_name)

        def raise_if_warranted(self):
            if Token._locked:
                raise self

    class TokenTeardownError (GameEngineError):

        message = "May not have completely removed {0} from the world."
        details = """\
                The {0}.{1}() method was invoked on a token that has already 
                been removed from the game world.  This is usually a sign that 
                not all references to this token were purged when it was 
                removed.  If you simply need to invoke the {1}() method after 
                teardown, label it with the kxg.after_teardown decorator."""

        def __init__(self, token, method):
            class_name = token.__class__.__name__
            method_name = method.__name__

            self.method = method
            self.format_arguments(class_name, method_name)

        def raise_if_warranted(self):
            if not hasattr(self.method, TokenMetaclass.after_teardown_flag):
                raise self


    def __new__(meta, name, bases, members):
        from types import FunctionType

        for member_name, member_value in members.items():
            is_function = (type(member_value) == FunctionType)
            is_before_setup = member_name in meta.before_setup_special_cases
            is_read_only = hasattr(member_value, meta.read_only_flag) or \
                    member_name in meta.read_only_special_cases

            if is_function and is_before_setup:
                member_value = TokenMetaclass.before_setup(member_value)
            if is_function and not is_read_only:
                member_value = TokenMetaclass.check_for_safety(member_value)

            members[member_name] = member_value

        return type.__new__(meta, name, bases, members)

    @classmethod
    def check_for_safety(meta, method):
        """ Decorate the given method so that it will complain if invoked in a 
        dangerous way.  This mostly means checking to make sure that methods 
        which alter the token are only called from messages. """

        # Access control checks help find bugs, but they may also incur 
        # significant computational expense.  By invoking python with 
        # optimization enabled (i.e. passing -O) these checks are disabled.  

        if not __debug__:
            return method

        @functools.wraps(method)
        def decorator(self, *args, **kwargs):
            if self.is_before_setup():
                meta.TokenSetupError(self, method).raise_if_warranted()

            elif self.is_registered():
                NullTokenIdError(self).raise_if_warranted()
                meta.TokenAccessError(self, method).raise_if_warranted()

            elif self.is_after_teardown():
                meta.TokenTeardownError(self, method).raise_if_warranted()

            else:
                UnknownTokenStatus(self).raise_unconditionally()

            return method(self, *args, **kwargs)

        return decorator

    @classmethod
    def read_only(meta, method):
        setattr(method, meta.read_only_flag, True)
        return method

    @classmethod
    def before_setup(meta, method):
        setattr(method, meta.before_setup_flag, True)
        return method

    @classmethod
    def after_teardown(meta, method):
        setattr(method, meta.after_teardown_flag, True)
        return method


class Token (object):

    __metaclass__ = TokenMetaclass

    _locked = True
    _before_setup = 'before setup'
    _registered = 'registered'
    _after_teardown = 'after teardown'

    def __init__(self):
        self._id = None
        self._status = Token._before_setup
        self._extensions = {}

    def __repr__(self):
        return str(self)

    def __extend__(self):
        return {}


    def setup(self):
        pass

    def update(self, time):
        pass

    @read_only
    def report(self, messenger):
        pass

    def teardown(self):
        pass


    @read_only
    def get_id(self):
        return self._id

    @before_setup
    def give_id(self, id):
        assert hasattr(self, '_id'), "Forgot to call Token.__init__() in subclass constructor."
        assert self._id is None, "Token already has an id."
        assert self.is_before_setup(), "Token already registered with the world."
        assert isinstance(id, IdFactory), \
                "Must use an IdFactory instance to give an id."
        self._id = id.next()

    @read_only
    def is_before_setup(self):
        before_setup = Token._before_setup
        return getattr(self, '_status', before_setup) == before_setup

    @read_only
    def is_registered(self):
        return getattr(self, '_status', None) == Token._registered

    @read_only
    def is_after_teardown(self):
        return getattr(self, '_status', None) == Token._after_teardown

    @read_only
    def get_extension(self, actor):
        return self._extensions[type(actor)]

    @read_only
    def get_extensions(self):
        return self._extensions.values()


class World (Token):

    def __init__(self):
        Token.__init__(self)

        self._id = 1
        self._tokens = {1: self}
        self._actors = []

    @read_only
    def __str__(self):
        return '<World len=%d>' % len(self)

    @read_only
    def __iter__(self):
        for token in self._tokens.values():
            yield token

    @read_only
    def __len__(self):
        return len(self._tokens)

    @read_only
    def __contains__(self, token):
        return token.get_id() in self._tokens


    def update(self, time):
        for token in self:
            if token is not self:
                token.update(time)

    @before_setup
    def define_actors(self, actors):
        self._actors = actors

    def add_token(self, token, list=None):
        id = token.get_id()
        assert id is not None, "Can't register a token with a null id."
        assert id not in self._tokens, "Can't reuse %d as an id number." % id
        assert isinstance(id, int), "Token has non-integer id number."

        self._tokens[id] = token
        if list is not None:
            list.append(token)

        token._extensions = {}
        extension_classes = token.__extend__()

        for actor in self._actors:
            actor_class = type(actor)
            extension_class = extension_classes.get(actor_class)

            if extension_class:
                extension = extension_class(actor, token)
                token._extensions[actor_class] = extension

        token._status = Token._registered
        token.setup(self)

        for extension in token.get_extensions():
            extension.setup()

    def add_tokens(self, tokens, list=None):
        for token in tokens:
            self.add_token(token, list)

    def remove_token(self, token, list=None):
        id = token.get_id()
        assert id is not None, "Can't remove a token with a null id."
        assert isinstance(id, int), "Token has non-integer id number."
        assert token.is_registered(), "Can't remove an unregistered token."

        del self._tokens[id]
        if list is not None:
            list.remove(token)

        for extension in token.get_extensions():
            extension.teardown()

        token.teardown()
        token._status = Token._after_teardown

    def remove_tokens(self, tokens, list=None):
        for token in tokens:
            self.remove_token(token, list)

    def handle_message(self, message):
        message.execute(self)


    @read_only
    def get_token(self, id):
        return self._tokens[id]

    def has_game_started(self):
        raise NotImplementedError

    def has_game_ended(self):
        raise NotImplementedError


class Prototype (Token):

    def __init__(self, id):
        Token.__init__(self, id)
        self._instantiated = False

    @check_for_prototype
    def instantiate(self, id):
        from copy import deepcopy
        instance = deepcopy(self)
        Token.__init__(instance, id)
        instance._instantiated = True
        return instance

    def check_for_prototype(self):
        assert not self._instantiated

    def check_for_instance(self):
        assert self._instantiated


class TokenExtension (object):
    def __init__(self, actor, token):
        pass

class TokenSerializer (object):

    def __init__(self, world):
        self.world = world

    def pack(self, message):
        from pickle import Pickler
        from cStringIO import StringIO

        buffer = StringIO()
        delegate = Pickler(buffer)

        delegate.persistent_id = self.persistent_id
        delegate.dump(message)

        return buffer.getvalue()

    def unpack(self, packet):
        from pickle import Unpickler
        from cStringIO import StringIO

        buffer = StringIO(packet)
        delegate = Unpickler(buffer)

        delegate.persistent_load = self.persistent_load
        return delegate.load()

    def persistent_id(self, token):
        if isinstance(token, Token):
            if token.is_registered():
                return token.get_id()
            if token.is_after_teardown():
                raise UsingDestroyedToken(token)

    def persistent_load(self, id):
        return self.world.get_token(int(id))


class UnrestrictedTokenAccess (object):

    def __enter__(self):
        Token._locked = False

    def __exit__(self, *args, **kwargs):
        Token._locked = True



class Message (object):

    def __repr__(self):
        return self.__str__()

    def check(self, world, sender_id):
        """ Return true if the message is consistent with the state of the game 
        world.  This is one of the most important message callbacks and should 
        be reimplemented every subclass.  It first invoked on the client side 
        to prevent bad requests from using up network bandwidth.  It is then 
        invoked again on the server, to prevent out-of-sync errors or hacked 
        messages.

        Since the role of this callback is simply to report on the validity of 
        the message, it should not make any changes to anything.  Any changes 
        made to the game world, for example, will lead to bugs because this 
        method is only called on one of the clients.  The game engine makes 
        some effort to prevent these kinds of errors, but it isn't bulletproof.

        :argument world: The game world.
        :argument sender: A number specific to the actor sending this message.
        :returns:  Boolean indicating if the message is valid. """

        # At first, it may seem strange that this method is passed an id number 
        # rather than an actor object.  The reason is that the server-side has 
        # RemoteActor objects, which are very different from normal actors.

        raise NotImplementedError

    def setup(self, world, id_factory):
        """ Setup the Allow the message to claim unique ID numbers for new 
        objects being created.  This method is only called once (e.g. on the 
        server) to guarantee that the given ID numbers are unique.
        
        :argument world: The game world.
        :argument id_factory: An object that returns id numbers for new tokens.
        :returns: None """

        pass

    def reject(self, sender):
        """ Inform *sender* that the message was rejected.  This means that 
        :meth:`check` returned false, either locally or on the server.  In many 
        cases, this happens because the player requests some sort of illegal 
        action, like building a unit without having enough resource.  This 
        callback should be overwritten to provide the player feedback about 
        what they did wrong.  By default, this method will raise an 
        :exc:`UnhandledMessageRejection` so that rejected messages don't go 
        unnoticed.

        :argument sender: The actor that sent this message.
        :returns: None """

        def default_handler(message):
            raise UnhandledMessageRejection(self)

        callback = self._callback_helper(sender, 'reject_{}', default_handler)
        callback(self)
        

    def accept(self, sender, verified):
        """ Inform *sender* that the message was accepted.  This means that 
        :meth:`check` returned true, either locally or on the server.  If the 
        message was accepted locally, it could still be rejected by the server 
        and so the *verified* parameter is set to false.  Otherwise, if the 
        server has accepted the message, *verified* is set to true.  This 
        callback can be overwritten to provide instantaneous feedback to 
        players while the message is traveling to and from the server.

        :arguments sender: The actor that sent this message.
        :arguments verified: A boolean indicating who accepted this message.
        :returns: None """

        callback = self._callback_helper(sender, 'accept_{}')
        callback(self, verified)
        
    def execute(self, world):
        """ Allow the message to make modifications to the game world.  This
        will be called exactly once on each host, but may be called more than
        once on a single message object.  (This is because message objects may
        be pickled and sent over the network.)  So one call to this method
        should not affect a second call. """

        raise NotImplementedError

    def notify(self, actor, was_sent_from_here):
        """ Inform the given actor that this message has occurred.  This will 
        only happen on the machine that is hosting the actor in question.  For 
        example, the actor representing a player on the server will not be 
        notified, but the actor representing that player on a client will. """

        callback = self._callback_helper(actor, 'handle_{}')
        callback(self, was_sent_from_here)


    @classmethod
    def type(cls):
        """ Return a string indicating what type of message this is.  This is 
        used by actors to decide which callback to invoke upon receiving this 
        kind of message.  By default, this method returns the class name 
        converted to box_car_case and should not need to be overridden.  If it 
        is overridden, make sure the string it returns is always a valid python 
        identifier. """
        import re

        camel_case_name = cls.__name__
        lower_case_words = [word.group(0).lower()
            for word in re.finditer('[A-Z][a-z]*', camel_case_name)]

        return '_'.join(lower_case_words)

    def copy(self):
        """ Return a shallow copy of the message object.  This is called by
        the game engine just before the message is delivered to the actors, so
        that the game can provide information specific to certain actors. """
        import copy
        return copy.copy(self)

    def set_status(self, status):
        self._status = status

    def set_origin(self, sent_from_here):
        self._origin = sent_from_here
    
    def was_accepted(self):
        return self._status is True

    def was_rejected(self):
        return self._status is False

    def was_sent_from_here(self):
        return self._origin

    def was_sent_by_referee(self, sender):
        return sender == 0

    def _callback_helper(self, handler, 
            callback_name, default_callback=lambda *args: None):

        message_type = self.type()
        callback_name = callback_name.format(message_type)

        if hasattr(handler, callback_name):
            return getattr(handler, callback_name)
        else:
            return default_callback


class IdMessage (object):
    def __init__(self, id):
        self.id = id


