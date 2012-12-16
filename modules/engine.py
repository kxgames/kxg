from __future__ import division

import pygame
import functools

# Things to Do
# ============
# 1. Allow each Actor to specify its own frame rate.  
# 2. Write comments, maybe create a sphinx page.
# 3. Have message.check() return None if successful and something else 
# otherwise.  Then pass the value returned by check() into reject(), so the 
# game can handle errors appropriately.

# It's annoying that game objects can't send messages.  Often the referee 
# update function ends up looking like something that should be inside the 
# update function for a specific token.  It's also a little annoying that the 
# referee has to be able to receive messages, because it never reacts to them.  
# (That's kinda what the message.execute callback is for.)  I have a feeling 
# that both these problems could be solved in one change, which would basically 
# involve removing the referee, although I haven't put much thought into it.

class MainLoop (object):
    """ Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages. """

    def play(self, frequency=50):
        try:
            clock = pygame.time.Clock()
            self.stop_flag = False

            stage = self.get_initial_stage()
            stage.set_master(self)
            stage.setup()

            while not self.is_finished():
                time = clock.tick(frequency) / 1000
                stage.update(time)

                if stage.is_finished():
                    stage.teardown()
                    stage = stage.get_successor()

                    if stage:
                        stage.set_master(self)
                        stage.setup()
                    else:
                        self.exit()

            if stage:
                stage.teardown()

        except KeyboardInterrupt:
            print

    def exit(self):
        self.stop_flag = True

    def get_initial_stage(self):
        raise NotImplementedError

    def is_finished(self):
        return self.stop_flag


class MultiplayerDebugger (object):
    """ Simultaneously plays any number of different game loops, by executing
    each loop in its own process.  This greatly facilitates the debugging and
    testing multiplayer games. """

    import multiprocessing

    class Process(multiprocessing.Process):

        def __init__(self, name, loop):
            constructor = MultiplayerDebugger.multiprocessing.Process.__init__
            constructor(self, name=name)
            self.loop = loop

        def __nonzero__(self):
            return self.is_alive()

        def run(self):
            try: self.loop.play()
            except KeyboardInterrupt:
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

    def __init__(self, world, mailbox, actors):
        Stage.__init__(self)
        self.world = world
        self.mailbox = mailbox
        self.actors = actors

    def setup(self):
        """ Prepares the actors, world, and messaging system to begin playing
        the game.  This function is only called once, and is therefore useful
        for initialization code. """

        # Setup the mailbox, then immediately collect any greeting messages
        # that have been sent.  Doing this guarantees that the greetings are
        # processed before any other messages.  Once the actor setup methods
        # are called, other messages may go on the queue.

        self.mailbox.setup(self.world, self.actors)
        self.mailbox.collect()

        # Setup the world before setting up the actors, so that the actors can
        # feel free to read information out of the world when building
        # themselves.

        with UnprotectedTokenLock():
            self.world.setup()

        for actor in self.actors:
            actor.setup(self.world)

    def update(self, time):
        """ Sequentially updates the actors, world, and messaging system.  The
        loop terminates once all of the actors indicate that they are done.  """

        self.mailbox.collect()
        self.mailbox.update()

        with UnprotectedTokenLock():
            self.world.update(time)

        still_playing = False

        for actor in self.actors:
            with ProtectedTokenLock(actor):
                actor.update(time)
            if not actor.is_finished():
                still_playing = True

        if not still_playing:
            self.exit_stage()

    def teardown(self):
        for actor in self.actors:
            actor.teardown()

        with UnprotectedTokenLock():
            self.world.teardown()


class SinglePlayerGameStage (GameStage):
    def __init__(self, world, referee, remaining_actors):
        mailbox = LocalMailbox()
        actors = [referee]

        if isinstance(remaining_actors, dict):
            for actor, greeting in remaining_actors.items():
                actor.send_message(greeting)
                actors.append(actor)
        else:
            actors.extend(remaining_actors)

        GameStage.__init__(self, world, mailbox, actors)

class MultiplayerClientGameStage (GameStage):
    def __init__(self, world, actor, pipe):
        mailbox = RemoteMailbox(pipe)
        GameStage.__init__(self, world, mailbox, [actor])

class MultiplayerServerGameStage (GameStage):
    def __init__(self, world, referee, pipes):
        mailbox = LocalMailbox()
        actors = [referee]

        if isinstance(pipes, dict):
            for pipe, greeting in pipes.items():
                actor = RemoteActor(pipe)
                actor.send_message(greeting)
                actors.append(actor)
        else:
            actors += [RemoteActor(pipe) for pipe in pipes]
            
        GameStage.__init__(self, world, mailbox, actors)


class Actor (object):

    def __init__(self):
        self.ambassador = self.get_name()
        self.messages = []
        self.finished = False
        self.greeted = False

    def get_name(self):
        raise NotImplementedError

    def setup(self, world):
        raise NotImplementedError

    def update(self, time):
        raise NotImplementedError

    def teardown(self):
        raise NotImplementedError

    def finish(self):
        self.finished = True

    def is_finished(self):
        return self.finished


    def send_message(self, message):
        self.messages.append(message)

    def deliver_messages(self):
        buffer = self.messages; self.messages = []
        return buffer

    def accept_message(self, message, verified):
        message.accept(self, verified)

    def reject_message(self, message):
        message.reject(self)

    def dispatch_message(self, message):
        pass

    def receive_message(self, message):
        self.receive_greeting(message)
        message.notify(self, message.was_sent_from_here())

    def receive_greeting(self, message):
        # A greeting is a special type of message that specifies which player
        # is associated with this actor.  Only messages that are subclasses of
        # the base Greeting class and that were sent by this actor will be
        # interpreted as greetings.  It is an error for one actor to receive
        # more than one greeting.
        
        if isinstance(message, Greeting) and message.was_sent_from_here():
            if self.greeted:
                raise ActorGreetedTwice()
            else:
                self.ambassador = message.get_sender()
                self.greeted = True


class RemoteActor (Actor):

    def __init__(self, pipe):
        Actor.__init__(self)
        self.pipe = pipe
        self.pipe.lock()

        # This is a little hacky, but it allows the server to exit once the
        # referee is finished.  This works because the game stage won't stop
        # executing until all of the actors report that they are finished.
        #self.finish()

    def get_name(self):
        return "remote"

    def is_finished(self):
        return self.pipe.finished()

    def setup(self, world):
        self.world = world

    def update(self, time):
        self.pipe.deliver()

    def teardown(self):
        pass

    def deliver_messages(self):
        for message in self.pipe.receive():
            message.unpack(self.world)
            self.send_message(message)

        return Actor.deliver_messages(self)

    def accept_message(self, message, verified):
        pass

    def reject_message(self, message):
        message.set_origin(True)
        message.pack(self.world)
        self.pipe.send(message)

    def dispatch_message(self, message):
        message.pack(self.world)
        self.pipe.send(message)

    def receive_message(self, message):
        self.receive_greeting(message)


class Referee (Actor):
    def __init__(self):
        Actor.__init__(self)

class Mailbox (object):

    def setup(self, world, actors):
        raise NotImplementedError

    def collect(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError


class LocalMailbox (Mailbox):

    def setup(self, world, actors):
        self.world = world
        self.actors = actors
        self.packages = []
        self.id_factory = IdFactory(world)

    def collect(self):
        for actor in self.actors:
            messages = actor.deliver_messages()
            self.packages += [ (actor, message) for message in messages ]

    def update(self):
        packages = self.packages
        self.packages = []

        for sender, message in packages:
            status = message.check(self.world, sender.ambassador)
            message.set_status(status)

            if message.was_accepted():
                sender.accept_message(message, True)
            else:
                sender.reject_message(message)
                continue

            message.setup(self.world, sender.ambassador, self.id_factory)

            for actor in self.actors:
                private_message = message.copy()
                private_message.set_origin(actor is sender)
                actor.dispatch_message(private_message)

            with UnprotectedTokenLock():
                message.execute(self.world)

            for actor in self.actors:
                private_message = message.copy()
                private_message.set_origin(actor is sender)
                with ProtectedTokenLock(actor):
                    actor.receive_message(private_message)


class RemoteMailbox (Mailbox):

    def __init__(self, pipe):
        self.pipe = pipe
        self.pipe.lock()

    def setup(self, world, actors):
        assert len(actors) == 1
        self.world = world
        self.actor = actors[0]
        self.messages = []

    def collect(self):
        self.messages += self.actor.deliver_messages()

    def update(self):
        actor = self.actor
        ambassador = actor.ambassador

        for message in self.messages:
            status = message.check(self.world, ambassador)

            if status:
                actor.accept_message(message, False)
            else:
                actor.reject_message(message)
                continue

            message.pack(self.world)
            self.pipe.send(message)

        self.pipe.deliver()
        self.messages = []

        for message in self.pipe.receive():
            message.unpack(self.world)

            if message.was_sent_from_here():
                if message.was_accepted():
                    actor.accept_message(message, True)
                else:
                    actor.reject_message(message)
                    continue

            with UnprotectedTokenLock():
                message.execute(self.world)

            with ProtectedTokenLock(actor):
                actor.receive_message(message)


class IdFactory (object):

    def __init__(self, world):
        self.next_id = world.get_id() + 1

    def next(self, count=1):

        if count == 1:
            result = self.next_id
            self.next_id += 1

        else:
            result = tuple(( self.next_id + n for n in range(count) ))
            self.next_id += count

        return result



def check_for_safety(method):
    @functools.wraps(method)
    def decorator(self, *args, **kwargs):
        # I don't understand exactly how this works, but wrapping the decorator 
        # function with the `functools' method allows pickle to understand the 
        # decorator.
        self.check_for_safety()
        return method(self, *args, **kwargs)
    return decorator

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


class Token (object):

    _access = 'protected'
    _actor = None

    def __init__(self):
        self._id = None
        self._registered = False
        self._extensions = {
                actor : extension_class(self)
                for actor, extension_class in self.__extend__().items() }

    def __getattr__(self, key):
        # Don't recursively look for the '_extensions' attribute.  When the
        # token is being unpickled, this method is called before that attribute
        # is defined. 

        if key == '_extensions':
            return {}

        # Search for the extension that correspond to the currently active
        # actor and defer any unknown attribute accesses onto it.

        actor = Token._actor
        extension = self._extensions.get(actor)

        if extension and hasattr(extension, key):
            return getattr(extension, key)
        else:
            raise AttributeError(key)

    def __extend__(self):
        return {}


    def register(self, id):
        assert self._id is None
        self._id = id.next() if isinstance(id, IdFactory) else id

    def setup(self, world):
        pass

    def update(self, time):
        pass

    def teardown(self):
        pass


    def get_id(self):
        return self._id

    def get_extension(self):
        actor = Token._actor
        extension = self._extensions.get(actor)

        if extension: return extension
        else: raise AttributeError

    def check_for_safety(self):
        assert self._id is not None, "Token has a null id."
        assert self._access == 'unprotected', "Don't have permission to modify token."
        assert self._registered == True, "Token never added to world."


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


class World (Token):

    def __init__(self):
        Token.__init__(self)
        self._tokens = {}
        self._registered = True

    def __iter__(self):
        for token in self._tokens.values():
            yield token

    def __len__(self):
        return len(self._tokens)

    def __contains__(self, token):
        return token.get_id() in self._tokens

    def get_token(self, id):
        return self._tokens[id]

    @check_for_safety
    def add_token(self, token):
        id = token.get_id()
        assert id is not None, "Can't register a token with a null id."
        assert isinstance(id, int)

        token._registered = True
        self._tokens[id] = token

    def setup(self):
        raise NotImplementedError

    def update(self, time):
        raise NotImplementedError

    def teardown(self):
        raise NotImplementedError


class TokenExtension (object):
    def __init__(self, token):
        pass

class TokenLock:

    def __init__(self, access, actor=None):
        self.current_access = access
        self.current_actor = actor

    def __enter__(self):
        self.previous_access = Token._access
        self.previous_actor = Token._actor

        Token._access = self.current_access
        Token._actor = self.current_actor

    def __exit__(self, *args, **kwargs):
        Token._access = self.previous_access
        Token._actor = self.previous_actor

    @staticmethod
    def restrict_default_access():
        Token._access = 'protected'

    @staticmethod
    def allow_default_access():
        Token._access = 'unprotected'


class ProtectedTokenLock (TokenLock):

    def __init__(self, actor):
        TokenLock.__init__(self, 'protected', actor.get_name())


class UnprotectedTokenLock (TokenLock):

    def __init__(self):
        TokenLock.__init__(self, 'unprotected', None)



class Message (object):

    def check(self, world, sender):
        """ Returns true if the message is consistent with the state of the
        game world.  This method may be called several times on different
        hosts, and for that reason it is not able to modify the game world. """
        pass

    def reject(self, actor):
        raise UnhandledMessageRejection(self)

    def accept(self, actor, pending):
        pass

    def setup(self, world, sender, id_factory):
        """ Allows the message to claim unique ID numbers for new objects being
        created.  In multiplayer games, this method is only called on the
        server to guarantee that the given ID numbers are unique. """
        pass

    def execute(self, world):
        """ Allows the message to make modifications to the game world.  This
        will be called exactly once on each host, but may be called more than
        once on a single message object.  (This is because message objects may
        be pickled and sent over the network.)  So one call to this method
        should not affect a second call. """
        pass

    def notify(self, actor):
        """ Informs an actor that this message has occurred.  This will only
        happen on the machine that is hosting the actor in question.  For
        example, the actor representing a player on the server will not be
        notified, but the actor representing that player on a client will. """
        pass


    def copy(self):
        """ Returns a shallow copy of the message object.  This is called by
        the game engine just before the message is delivered to the actors, so
        that the game can provide information specific to certain actors. """
        import copy
        return copy.copy(self)

    def pack(self, world):
        """ Modifies the message such that it can be faithfully pickled and
        sent over the network.  This primarily involves sending token ID
        numbers rather than tokens themselves. """

        packing_list = {}

        for name in dir(self):
            attribute = getattr(self, name)
            if isinstance(attribute, Token):
                if attribute in world:
                    packing_list[name] = attribute.get_id()
                    delattr(self, name)
        
        assert not hasattr(self, '_packing_list')
        self._packing_list = packing_list

    def unpack(self, world):
        """ Rebuild a messages that was just sent across the network and
        unpickled.  This primarily involves converting token ID numbers back
        into real token objects. """

        assert hasattr(self, '_packing_list')
        packed_tokens = self._packing_list.items()
        del self._packing_list

        for name, id in packed_tokens:
            token = world.get_token(id)
            setattr(self, name, token)

    def set_status(self, status):
        self._status = status

    def set_origin(self, sent_from_here):
        self._origin = sent_from_here
    
    def was_accepted(self):
        return self._status == True

    def was_rejected(self):
        return self._status == False

    def was_sent_from_here(self):
        return self._origin


class Greeting (Message):
    def get_sender(self):
        raise NotImplementedError


