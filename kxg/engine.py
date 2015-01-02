import pyglet, functools

# Things to Improve (fold)
# =================
# 1. Maybe move MultiplayerDebugger into a new 'quickstart' module.
#
# 2. The server will crash if it receives a packet it doesn't understand.  I 
#    should add to the network module the ability to define a "bad packet 
#    handler" that gets called whenever a packet is received that couldn't be 
#    understood.  On the server, this handler would log an error and maybe fire 
#    a message to the client explaining the problem.  On the client, this would 
#    just log an error I guess.
#
# 3. I should move the networking code into its own module.  I like the name
#    "linersock" with the tagline "The layer between you and your sockets that 
#    helps prevent chafing!".  But another option is "supersocker"...


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
            without being assigned an id number.  To correct this, make sure 
            that you're using a CreateToken message to create this token."""

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



class Loop:
    """ Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages. """

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


class GuiLoop (Loop):

    def play(self, frames_per_sec=50):
        self.window = pyglet.window.Window()
        Loop.play(self, frames_per_sec)

    def get_window(self):
        return self.window


class MultiplayerDebugger:
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



class Stage:

    def __init__(self):
        self._stop_flag = False

    def get_loop(self):
        return self._loop

    def set_loop(self, loop):
        self._loop = loop

    def exit_stage(self):
        """ Stop this stage from executing once the current update ends. """
        self._stop_flag = True

    def exit_program(self):
        """ Exit the game once the current update ends. """
        self._loop.exit()

    def is_finished(self):
        """ Return true if this stage is done executing. """
        return self._stop_flag

    def get_successor(self):
        """ Create and return the stage that should be executed next. """
        return None

    def on_enter_stage(self):
        raise NotImplementedError

    def on_update_stage(self, dt):
        raise NotImplementedError

    def on_exit_stage(self):
        raise NotImplementedError


class GameStage (Stage):

    def __init__(self, world, forum, actors):
        Stage.__init__(self)
        self.world = world
        self.forum = forum
        self.actors = actors
        self.successor = None

    def on_enter_stage(self):
        """
        Prepare the actors, the world, and the messaging system to begin 
        playing the game.
        
        This function is guaranteed to be called exactly once upon entering the 
        game stage.  Therefore it is used for initialization code.
        """

        # 1. Setup the forum.

        self.forum.on_start_game(self.world, self.actors)

        # 2. Setup the world.

        self.world.define_actors(self.actors)
        self.world._status = Token._registered

        with unrestricted_token_access():
            self.world.on_start_game()

        # 3. Setup the actors.  Because this is done once the forum and the  
        #    world have been setup, this signals to the actors that they can 
        #    send messages and query the game world as usual.

        for actor in self.actors:
            actor.on_start_game(self.world)

    def on_update_stage(self, dt):
        """ Sequentially updates the actors, world, and messaging system.  The
        loop terminates once all of the actors indicate that they are done. """

        still_playing = False

        for actor in self.actors:
            actor.on_update_game(dt)
            if not actor.is_finished():
                still_playing = True

        if not still_playing:
            self.exit_stage()

        self.forum.on_update_game()

        with unrestricted_token_access():
            self.world.on_update_game(dt)

    def on_exit_stage(self):
        self.forum.on_finish_game()

        for actor in self.actors:
            actor.on_finish_game()

        with unrestricted_token_access():
            self.world.on_finish_game()

    def get_successor(self):
        return self.successor

    def set_successor(self, successor):
        self.successor = successor


class SinglePlayerGameStage (GameStage):

    def __init__(self, world, referee, other_actors):
        forum = Forum()
        actors = [referee] + other_actors
        GameStage.__init__(self, world, forum, actors)


class MultiplayerClientGameStage (Stage):

    def __init__(self, world, actor, pipe):
        Stage.__init__(self)

        self.world = world
        self.actor = actor
        self.forum = RemoteForum(pipe)

    def setup(self):
        pass

    def update(self, dt):
        if self.forum.connect():
            self.exit_stage()

    def teardown(self):
        pass

    def get_successor(self):
        return GameStage(self.world, self.forum, [self.actor])


class MultiplayerServerGameStage (GameStage):

    def __init__(self, world, referee, pipes):
        forum = Forum()
        actors = [referee] + [RemoteActor(x) for x in pipes]
        GameStage.__init__(self, world, forum, actors)



class Forum:

    def __init__(self):
        self.world = None
        self.actors = None

    def dispatch_message(self, message):
        # This function encapsulates the message handling logic that's meant to 
        # be run on every machine participating in the game.  In other words, 
        # this code gets run more that once for each message.  For that reason, 
        # nothing in this function should make any changes to the message.  The 
        # make_temporarily_immutable() context manager enforces this to an 
        # extent, but it can be tricked so you still need to be careful.

        with message.make_temporarily_immutable():

            # Normally, tokens can only call methods that have been decorated 
            # with @read_only.  This is a precaution to help keep the worlds in 
            # sync on all the clients.  This restriction is lifted when the 
            # tokens themselves are handling messages, but enforced again once 
            # the actors are handling messages.

            with unrestricted_token_access():

                # First, let the message update the state of the game world.

                message.on_execute(self.world)

                # Second, let the world react to the message.  The main effect 
                # of the message should have already been carried out above.  
                # These callbacks should take care of more peripheral effects.

                self.world.react_to_message(message)

            # Third, let the actors and the extensions react to the message.  
            # This step is carried out last so that the actors can be sure that 
            # the world has a consistent state by the time their handlers are 
            # called.

            for actor in self.actors:
                actor.react_to_message(message)

    def on_start_game(self, world, actors):
        self.world = world
        self.actors = actors

        world.set_forum(self)

        # Give each actor a factory it can use to generate unique token ids.
        #
        # In multiplayer games, each client needs the ability to create tokens, 
        # so that messages can be instantly handled.  Tokens still need unique 
        # ids though, so this method provides each actor with an IdFactory that 
        # generates ids using an offset and a spacing to ensure uniqueness.
        #
        # Actors take their own id numbers (used for figuring out who messages 
        # were sent by) from the offset parameter of the id factory.  Since the 
        # Referee must have an id of 0 if it's present, care is taken to make 
        # that happen.

        spacing = len(self.actors)
        actors = sorted(actors, key=lambda x: isinstance(x, Referee))

        for offset, actor in enumerate(actors):
            id_factory = IdFactory(world, offset, spacing)
            actor.set_forum(self, id_factory)

    def on_update_game(self):
        # The base forum doesn't do anything on a timer; it does everything in 
        # response to a message being sent.  But the RemoteForum uses this 
        # method to react to message that have arrived from the server.
        pass

    def on_finish_game(self):
        pass


class ForumObserver:

    from collections import namedtuple
    CallbackInfo = namedtuple('CallbackInfo', 'message_cls, callback')

    def __init__(self):
        # Create a data structure to hold all the callbacks registered with 
        # this observer.  Using a dictionary to distinguish between the regular 
        # message handlers, the soft sync error handlers, and the hard sync 
        # error handlers (instead of just having three different lists) makes 
        # it easy to write protected helpers to do most of the work.  

        self._callbacks = {
                'message': [],
                'soft_sync_error': [],
                'hard_sync_error': [],
        }

        # Allow subclasses to easily disable all forum observation behavior by 
        # setting this flag.

        self._is_observation_allowed = True

        # Decorators can be used to automatically label methods that should be 
        # callbacks.  Here, we look for methods that have been labeled in this 
        # way and register them appropriately.

        from inspect import getmembers, ismethod

        for method_name, method in getmembers(self, ismethod):
            message_cls = getattr(method, '_handle_message', None)
            if message_cls: self.handle_message(message_cls, method)

            message_cls = getattr(method, '_handle_soft_sync_error', None)
            if message_cls: self.handle_soft_sync_error(message_cls, method)

            message_cls = getattr(method, '_handle_hard_sync_error', None)
            if message_cls: self.handle_hard_sync_error(message_cls, method)

    def handle_message(self, message_cls, callback):
        self._add_callback('message', message_cls, callback)

    def handle_soft_sync_error(self, message_cls, callback):
        self._add_callback('soft_sync_error', message_cls, callback)

    def handle_hard_sync_error(self, message_cls, callback):
        self._add_callback('hard_sync_error', message_cls, callback)

    def ignore_message(self, message_cls, callback=None):
        self._drop_callback('message', message_cls, callback)

    def ignore_soft_sync_error(self, message_cls, callback=None):
        self._drop_callback('soft_sync_error', message_cls, callback)

    def ignore_hard_sync_error(self, message_cls, callback=None):
        self._drop_callback('hard_sync_error', message_cls, callback)

    def react_to_message(self, message):
        self._call_callbacks('message', message)

    def react_to_soft_sync_error(self, message):
        self._call_callbacks('soft_sync_error', message)

    def react_to_hard_sync_error(self, message):
        self._call_callbacks('hard_sync_error', message)

    def _add_callback(self, event, message_cls, callback):
        assert self._is_observation_allowed
        callback_info = ForumObserver.CallbackInfo(message_cls, callback)
        self._callbacks[event].append(callback_info)

    def _drop_callback(self, event, message_cls, callback):
        assert self._is_observation_allowed

        # The [:] syntax is important, because it causes the same list object 
        # to be refilled with the new values.  Without it a new list would be 
        # created and the list in self.callbacks would not be changed.

        self._callbacks[event][:] = [
                callback_info for callback_info in self.callbacks[event]
                if (callback_info.message_cls is message_cls) and
                   (callback_info.callback is callback or callback is None)
        ]
        
    def _call_callbacks(self, event, message):
        assert self._is_observation_allowed

        # Call the callbacks stored in this observer.

        for callback_info in self._callbacks[event]:
            if isinstance(message, callback_info.message_cls):
                callback_info.callback(message)

        # Call the callbacks stored in nested observers.

        for observer in self._get_nested_observers():
            observer._call_callbacks(event, message)

    def _get_nested_observers(self):
        return []

    def _disable_forum_observation(self):
        self._is_observation_allowed = False


class Actor (ForumObserver):

    def __init__(self):
        super().__init__()
        self.world = None
        self._forum = None
        self._id_factory = None

    def set_world(self, world):
        assert self.world is None, "Actor already has world."
        self.world = world

    def set_forum(self, forum, id_factory):
        assert self._id_factory is None, "Actor already has id."
        self._id_factory = id_factory

        assert self._forum is None, "Actor already has forum."
        self._forum = forum

    def get_id(self):
        assert self._id_factory is not None, "Actor does not have id."
        return self._id_factory.offset

    def is_token_from_me(self, token):
        return token.get_id() in self._id_factory

    def is_finished(self):
        return self.world.has_game_ended()

    def send_message(self, message):
        # Indicate that the message was sent by this actor and give the message 
        # a chance to assign id numbers to the tokens it's creating, if it's a 
        # CreateToken message.  This is done before the message is checked so 
        # that the check can make sure valid ids were assigned.

        message.set_sender(self)

        if isinstance(message, CreateToken):
            message.on_assign_token_ids(self._id_factory)

        # Make sure that the message isn't requesting something that can't be 
        # done.  For example, make sure the players have enough resource when 
        # they're trying to buy things.  If the message fails the check, return 
        # False immediately.

        if not message.on_check(self.world, self)
            return False

        # Hand the message off to the forum to be applied to the world and 
        # relayed on to all the other actors (which may or may not be on 
        # different machines).

        self._forum.dispatch_message(message)
        return True

    def on_start_game(self):
        pass

    def on_update_game(self, dt):
        pass

    def on_finish_game(self):
        pass

    def _get_nested_observers(self):
        return (token.get_extension(self) for token in self.world)


class Referee (Actor):

    class Reporter:
        
        def __init__(self, referee):
            self.referee = None
            self.is_finished_reporting = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.is_finished_reporting = True

        def send_message(self, message):
            if self.is_finished_reporting:
                raise errors.StaleReporterError()
            else:
                self.referee.send_message(message)

    def set_forum(self, forum, id_factory):
        super().set_forum(forum, id_factory)
        assert self.get_id() == 0

    def on_update_game(self, dt):
        with Referee.Reporter(self) as reporter:
            for token in self.world:
                token.report(reporter)


class RemoteForum (Forum):

    def __init__(self, pipe):
        super().__init__()
        self.actor_id_factory = None
        self.pipe = pipe
        self.pipe.lock()

    def connect(self):
        """
        Listen for an id from the server.

        At the beginning of a game, each client receives an IdFactory from the 
        server.  This factory are used to give id numbers that are guaranteed 
        to be unique to tokens that created locally.  This method checks to see 
        if such a factory has been received  This method checks to see if such 
        a factory has been received.  If it hasn't, this method does not block 
        and immediately returns False.  If it has, this method returns True 
        after saving the factory internally.  At this point it is safe to enter 
        the GameStage.
        """
        for message in self.pipe.receive():
            if isinstance(message, IdFactory):
                self.actor_id_factory = message
                return True
        return False

    def dispatch_message(self, message):
        # Have the message update the local world like usual.

        super().dispatch_message(message)

        # Relay the message to a RemoteActor running on the server to update 
        # the world on all of the other machine playing the game as well.

        self.pipe.send(message)
        self.pipe.deliver()

    def dispatch_soft_sync_error(self, message):
        """
        Manage the response when the server reports a soft sync error.

        A soft sync error can happen when this client sends a message that 
        fails the check on the server.  If the reason for the failure isn't 
        very serious, then the server can decide to send it as usual in the 
        interest of a smooth gameplay experience.  When this happens, the 
        message is flagged as a soft sync error.

        The purpose of a soft sync error is to inform the clients that they 
        have become slightly out of sync with the server and to give them a 
        chance to get back in sync.  When a message is marked as a sync error, 
        it is also given the opportunity to save the information from the 
        server that would have prevented the error from occurring in the first 
        place.  Note that sync errors are only handled on clients.
        """

        with message.make_temporarily_immutable():

            # Synchronize the world.

            with unrestricted_token_access():
                message.on_soft_sync_error(self.world)
                self.world.react_to_soft_sync_error(message)

            # Synchronize the tokens.

            for actor in self.actors:
                actor.react_to_soft_sync_error(message)

    def dispatch_hard_sync_error(self, message):
        """
        Manage the response when the server reports a hard sync error.

        A hard sync error is produced when this client sends a message that the 
        server refuses to pass on to the other clients playing the game.  In 
        this case, the client must either undo the changes that the message 
        made to the world before being sent or crash.  Note that unlike a soft 
        sync error, a hard sync error is only reported to the client that sent 
        the offending message.
        """

        with message.make_temporarily_immutable():

            # Roll back changes that the original message made to the world.

            with unrestricted_token_access():
                message.on_hard_sync_error(self.world)
                self.world.react_to_hard_sync_error(message)

            # Give the actors a chance to react to the error.  For example, a 
            # GUI actor might inform the user that there are connectivity 
            # issues and that their last action was countermanded.

            for actor in self.actors:
                actor.react_to_hard_sync_error(message)

    def on_start_game(self, world, actors):
        # Setup the world an actors as usual.

        super().on_start_game(world, actors)

        # Make sure that there is in fact only one actor, and assign that actor 
        # the id factory received from the server.  Note that this id factory 
        # overwrites the one provided in the superclass method above.

        assert len(actors) == 1

        self.actor = actors[0]
        self.actor.set_forum(self, self.actor_id_factory)

        # Setup up the pipe to send messages containing references to tokens.

        serializer = TokenSerializer(world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self):
        # An attempt is made to immediately deliver any messages passed into 
        # relay_message(), but sometimes it takes more than one try to send a 
        # message.  So in case there are any messages waiting to be sent, the 
        # code below attempts to clear the queue every frame.

        self.pipe.deliver()

        # For each message received from the server:

        for message in self.pipe.receive():

            # Execute messages coming in from other clients.  Messages that are 
            # coming back in after being sent by this client have already been 
            # executed.  They are only being sent back because an error has 
            # been detected and needs to be handled.

            if not message.was_sent_by(self):
                super().dispatch_message(message)

            # If an incoming message has any error flags set, attempt to handle 
            # those as well.  A message coming from any client can have a soft 
            # sync error, but only messages that came from this client can have 
            # a hard sync error.

            if message.has_soft_sync_error(self):
                self.dispatch_soft_sync_error(message)

            if message.has_hard_sync_error(self):
                self.dispatch_hard_sync_error(message)

    def on_finish_game(self):
        self.pipe.pop_serializer()


class RemoteActor (Actor):

    def __init__(self, pipe):
        super().__init__(self)
        self._disable_forum_observation()

        self.pipe = pipe
        self.pipe.lock()

    def set_forum(self, forum, id):
        super().set_forum(forum, id)
        self.pipe.send(id)

    def is_finished(self):
        return self.pipe.finished() or Actor.is_finished(self)

    def send_message(self):
        raise NotImplementedError

    def react_to_message(self, message):
        if not message.was_sent_by(self):
            self.pipe.send(message)
            self.pipe.deliver()

    def on_start_game(self, world):
        serializer = TokenSerializer(world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self, dt):
        # For each message received from the connected client:

        for message in self.pipe.receive():

            # Check the message to make sure it matches the state of the game 
            # world on the server.  If the message doesn't pass the check, the 
            # client and server must be out of sync.  Decide whether the sync 
            # error is recoverable (i.e. soft) or not (i.e. hard).  Soft sync 
            # errors are relayed on to the rest of the game as usual and are 
            # given an opportunity to sync all the clients.  Hard sync errors 
            # are not not relayed and must be somehow undone on the client that 
            # sent the message.
            
            if not message.on_check(self.world, self):
                if message.on_check_for_soft_sync_error(self.world):
                    message.flag_soft_sync_error()
                    self.pipe.send(message)
                else:
                    message.flag_hard_sync_error()
                    self.pipe.send(message)
                    continue

            # Silently reject the message if it was sent by an actor with a 
            # different id that this one.  This should absolutely never happen 
            # because this actor gives its id to its client, so if a mismatch 
            # is detected it's really bad news.

            if not message.was_sent_by(self):
                continue

            # Execute the message if it hasn't been rejected yet.

            self._forum.dispatch_message(message)

        # Deliver any messages waiting to be sent.  This has to be done every 
        # frame because it sometimes takes more than one try to send a message.

        self.pipe.deliver()

    def on_finish_game(self):
        self.pipe.pop_serializer()


class IdFactory:

    def __init__(self, world, offset, spacing):
        self.offset = world.get_last_id() + offset
        self.spacing = spacing
        self.num_ids_assigned = 0

    def __contains__(self, id):
        return id % self.spacing == self.offset

    def next(self):
        next_id = self.num_ids_assigned * self.spacing + self.offset
        self.num_ids_assigned += 1
        return next_id



def handle_message(message_cls)
    def decorator(function):
        function._handle_message = message_cls
        return function
    return decorator

def handle_soft_sync_error(message_cls):
    def decorator(function):
        function._handle_soft_sync_error = message_cls
        return function
    return decorator

def handle_hard_sync_error(message_cls):
    def decorator(function):
        function._handle_hard_sync_error = message_cls
        return function
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


class Token (ForumObserver):
    __metaclass__ = TokenMetaclass

    _locked = True
    _before_setup = 'before setup'
    _registered = 'registered'
    _after_teardown = 'after teardown'

    class WatchedMethod:

        def __init__(self, method):
            self.method = method
            self.watchers = []

        def __call__(self, *args, **kwargs):
            self.method(*args, **kwargs)
            for watcher in self.watchers:
                watcher(*args, **kwargs)

        def add_watcher(self, watcher):
            self.watchers.append(watcher)


    def __init__(self):
        self._id = None
        self._status = Token._before_setup
        self._extensions = {}

    def __extend__(self):
        return {}

    @read_only
    def watch_method(self, method_name, callback):
        """
        Register the given callback to be called whenever the method with the 
        given name is called.  You can easily take advantage of this feature in 
        token extension by using the @watch_token decorator.
        """

        # Make sure a token method with the given name exists, and complain if 
        # nothing is found.

        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise TokenWatchingError(method_name)

        # Wrap the method in a WatchedMethod object, if that hasn't already 
        # been done.  This object manages a list of callback method and takes 
        # responsibility for calling them after the method itself has been 
        # called.

        if not isinstance(method, Token.WatchedMethod):
            setattr(token, method_name, Token.WatchedMethod(method))
            method = getattr(self, method_name)

        # Add the given callback to the watched method.

        method.add_watcher(callback)

    @read_only
    def get_id(self):
        return self._id

    @before_setup
    def give_id(self, id):
        assert hasattr(self, '_id'), "Forgot to call Token.__init__() in subclass constructor."
        assert self._id is None, "Token already has an id."
        assert self.is_before_setup(), "Token already registered with the world."
        assert isinstance(id, IdFactory), "Must use an IdFactory instance to give an id."
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

    def on_add_to_world(self, world):
        pass

    def on_update_game(self, dt):
        pass

    @read_only
    def on_report_to_referee(self, reporter):
        pass

    def on_remove_from_world(self):
        pass


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
        yield from self._tokens.values()

    @read_only
    def __len__(self):
        return len(self._tokens)

    @read_only
    def __contains__(self, token):
        return token.get_id() in self._tokens

    @before_setup
    def define_actors(self, actors):
        self._actors = actors

    @read_only
    def get_token(self, id):
        return self._tokens[id]

    def has_game_started(self):
        raise NotImplementedError

    def has_game_ended(self):
        raise NotImplementedError

    def on_start_game(self):
        pass

    def on_update_game(self, dt):
        for token in self:
            if token is not self:
                token.update(dt)

    def on_finish_game(self):
        pass

    def _add_token(self, token):
        id = token.get_id()
        assert id is not None, "Can't register a token with a null id."
        assert id not in self._tokens, "Can't reuse %d as an id number." % id
        assert isinstance(id, int), "Token has non-integer id number."

        self._tokens[id] = token
        token._status = Token._registered

        token.setup(self)

        token._extensions = {}
        extension_classes = token.__extend__()

        for actor in self._actors:
            actor_class = type(actor)
            extension_class = extension_classes.get(actor_class)

            if extension_class:
                extension = extension_class(actor, token)
                token._extensions[actor_class] = extension

        return token

    def _remove_token(self, token):
        id = token.get_id()
        assert id is not None, "Can't remove a token with a null id."
        assert isinstance(id, int), "Token has non-integer id number."
        assert token.is_registered(), "Can't remove an unregistered token."

        del self._tokens[id]

        for extension in token.get_extensions():
            extension.teardown()

        token.teardown()
        token._status = Token._after_teardown

    def _get_nested_observers(self):
        yield from self


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


class TokenExtension (ForumObserver):

    def __init__(self, actor, token):
        self.actor = actor
        self.token = token

        # Iterate through all of the extension methods to find ones wanting to 
        # "watch" the token, then configure the token to call these methods 
        # whenever a token method of the same name is called.
        
        from inspect import getmembers, ismethod

        for method_name, method in getmembers(self, ismethod):

            # Methods with the '_kxg_watch_token' attribute set should be set 
            # up to watch the token.  This attribute is typically set using the
            # @watch_token decorator.

            if not hasattr(method, '_kxg_watch_token'):
                break

            # Tell the token to call the extension method whenever the matching 
            # token method is called.

            token.watch_method(method_name, method)

    def send_message(self, message):
        return self.actor.send_message(message)


class TokenSerializer:

    def __init__(self, world):
        self.world = world

    def pack(self, message):
        from pickle import Pickler
        from io import BytesIO

        buffer = BytesIO()
        delegate = Pickler(buffer)

        delegate.persistent_id = self.persistent_id
        delegate.dump(message)

        return buffer.getvalue()

    def unpack(self, packet):
        from pickle import Unpickler
        from io import BytesIO

        buffer = BytesIO(packet)
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

def watch_token(method):
    """
    Mark a token extension method that should automatically be called when a 
    token method of the same name is called.

    This decorator must only be used on TokenExtension methods, otherwise it 
    will silently do nothing.  The reason is that the decorator itself can't do 
    anything but label the given method, because at the time of decoration the 
    token to watch isn't known.  The method is actually setup to watch a token 
    in the TokenExtension constructor, which searches for the label added here.  
    But other classes won't make this search and will silently do nothing.
    """
    method._kxg_watch_token = True

@contextlib.contextmanager
def unrestricted_token_access():
    # I feel like this should be a method of the world.  And tokens should look 
    # to the world in check_for_safety().  That would make it so you could do 
    # anything to a token before it becomes part of the world.
    Token._locked = False
    try: yield
    finally: Token._locked = True


class Message:

    class ErrorState:
        SOFT_SYNC_ERROR = 0
        HARD_SYNC_ERROR = 1


    def __init__(self):
        self.sender_id = None

    def __repr__(self):
        return self.__str__()

    def __setattr__(self, key, value):
        if not hasattr(self, '_locked'):
            self.__dict__[key] = value
        else:
            raise ImmutableMessageError(self)

    def get_messages(self):
        return [self]

    def set_sender(self, actor):
        self.sender_id = actor.get_id()

    def was_sent_by(self, actor):
        return self.sender_id == actor.get_id()

    def was_sent_by_referee(self):
        return self.sender_id == 0

    def flag_soft_sync_error(self):
        self._error_state = Message.ErrorState.SOFT_SYNC_ERROR

    def flag_hard_sync_error(self):
        self._error_state = Message.ErrorState.HARD_SYNC_ERROR

    def has_soft_sync_error(self):
        return getattr(self, '_error_state', None) == Message.ErrorState.SOFT_SYNC_ERROR

    def has_hard_sync_error(self):
        return getattr(self, '_error_state', None) == Message.ErrorState.HARD_SYNC_ERROR

    @contextlib.contextmanager
    def make_temporarily_immutable(self):
        try:
            self._locked = True
            yield
        finally:
            del self._locked

    def copy(self):
        """
        Return a shallow copy of the message object.
        
        This is called by the game engine just before the message is delivered 
        to the actors, so that the game can provide information specific to 
        certain actors.
        """
        import copy
        return copy.copy(self)


    def on_check(self, world, sender):
        # Called by the actor.  Normal Actor will not send if this returns 
        # false.  RemoteActor will decide if this is a hard or soft error.  It 
        # will relay soft errors but cancel hard errors.
        pass

    def on_check_for_soft_sync_error(self, world):
        # Called only by RemoteActor if check() returns False.  If this method 
        # returns True, the message will be relayed to the rest of the clients 
        # with the sync error flag set.  Otherwise the message will not be sent 
        # and the RemoteForum that sent the message will be instructed to undo 
        # it.  If a soft error is detected, this method should save information 
        # about the world that it could use to resynchronize all the clients.
        pass

    def on_execute(self, world):
        # Called by the forum on every machine running the game.  Allowed to 
        # make changes to the game world, but should not change the message 
        # itself.  Called before any signal-handling callbacks.
        pass

    def on_soft_sync_error(self, world):
        # Called by the forum upon receiving a message with the soft error flag 
        # set.  This flag indicates that the client that sent the message is 
        # slightly out of sync with the server, but that the message will be 
        # relayed as usual and that the clients should use the opportunity to 
        # quietly resynchronize themselves.  
        pass

    def on_hard_sync_error(self, world):
        # Called by RemoteForum only upon receiving a message with the hard 
        # error flag set.  This flag indicates that the server refused to relay 
        # the given message to the other clients, presumably because it was too 
        # far out of sync with the world on the server, and that the message 
        # needs to be undone on this client.  Only the RemoteForum that sent 
        # the offending message will call this method.
        raise UnhandledSyncError


class CompositeMessage(Message):

    def __init__(self, *messages):
        super().__init__(self)
        self.messages = messages

    def get_messages(self):
        return self.messages


class CreateToken (Message):

    def __init__(self, token):
        self.token = token

    def on_assign_token_ids(self, id_factory):
        # Called by Actor but not by RemoteActor, so it is guaranteed to be 
        # called exactly once.  Not really different from the constructor, 
        # except that the id_factory object is nicely provided.  That's useful 
        # for CreateToken but probably nothing else.  Could be called after 
        # check() to not waste id numbers, but that's not super important.
        self.token.give_id(id_factory)

    def on_check(self, world, sender):
        return self.token not in world and sender.is_token_from_me(self.token)

    def on_execute(self, world):
        world._add_token(self.token)

    def on_hard_sync_error(self, world):
        world._remove_token(self.token)


class DestroyToken (Message):

    def __init__(self, token):
        self.token = token

    def on_check(self, world, sender):
        return self.token in world

    def on_execute(self, world):
        world._remove_token(self.token)

    def on_hard_sync_error(self, world):
        world._add_token(self.token)


