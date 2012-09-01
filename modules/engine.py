from __future__ import division

import pygame

# Things to Do
# ============
# 1. Allow each Actor to specify its own frame rate.  
# 2. Write comments, maybe create a sphinx page.

class MainLoop (object):
    """ Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages. """

    def play(self, frequency=50):

        try:
            clock = pygame.time.Clock()
            self.stop_flag = False

            # All subclasses need to define self.stage.
            self.stage.setup()

            while not self.is_finished():
                time = clock.tick(frequency) / 1000
                self.stage.update(time)

                if self.stage.is_finished():
                    self.stage.teardown()
                    self.stage = self.stage.get_successor()
                    if self.stage: self.stage.setup()
                    else: self.exit()

            if self.stage:
                self.stage.teardown()

        except KeyboardInterrupt:
            print

    def exit(self):
        self.stop_flag = True

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

    def __init__(self, master_or_stage):
        if isinstance(master_or_stage, MainLoop):
            self.master = master_or_stage
        elif hasattr(master_or_stage, 'get_master'):
            self.master = master_or_stage.get_master()
        else:
            raise ValueError("Must provide stage with a parent object.")

        self.stop_flag = False

    def get_master(self):
        return self.master

    def exit_stage(self):
        """ Stop this stage from executing once the current update ends. """
        self.stop_flag = True

    def exit_program(self):
        """ Exit the game once the current update ends. """
        self.master.exit()

    def is_finished(self):
        """ Return true if this stage is done executing. """
        return self.stop_flag

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

    def __init__(self, master, world, mailbox, actors):
        Stage.__init__(self, master)

        self.world = world
        self.mailbox = mailbox
        self.actors = actors

    def setup(self):
        self.mailbox.setup(self.world, self.actors)

        with UnprotectedProxyLock():
            self.world.setup()

        for actor in self.actors:
            actor.setup(self.world)

    def update(self, time):
        with UnprotectedProxyLock():
            self.world.update(time)

        still_playing = False

        for actor in self.actors:
            with ProtectedProxyLock(actor):
                actor.update(time)
            if not actor.is_finished():
                still_playing = True

        self.mailbox.update()

        if not still_playing:
            self.exit_stage()

    def teardown(self):
        for actor in self.actors:
            actor.teardown()

        self.world.teardown()


class SinglePlayerGameStage (GameStage):
    def __init__(self, master, world, referee, actors_to_greetings):

        mailbox = LocalMailbox()
        actors = [referee]

        for actor, greeting in actors_to_greetings.items():
            actor.send_message(greeting)
            actors.append(actor)

        GameStage.__init__(self, master, world, mailbox, actors)

class MultiplayerClientGameStage (GameStage):
    def __init__(self, master, world, actor, pipe):

        mailbox = RemoteMailbox(pipe)
        GameStage.__init__(self, master, world, mailbox, [actor])

class MultiplayerServerGameStage (GameStage):
    def __init__(self, master, world, referee, pipes_to_greetings):

        mailbox = LocalMailbox()
        actors = [referee]

        for pipe, greeting in pipes_to_greetings.items():
            actor = RemoteActor(pipe)
            actor.send_message(greeting)
            actors.append(actor)
            
        GameStage.__init__(self, master, world, mailbox, actors)


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
        message.notify(self)

    def receive_greeting(self, message):
        # A greeting is a special type of message that specifies which player
        # is associated with this actor.  Only messages that are subclasses of
        # the base Greeting class and that were sent by this actor will be
        # interpreted as greetings.  It is an error for one actor to receive
        # more than one greeting.
        
        if isinstance(message, Greeting) and message.was_sent_from_here():
            if self.greeted: raise ActorGreetedTwice()
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

    def is_finished(self):
        return self.pipe.finished()
        #return not self.pipe.busy()

    def get_name(self):
        return "__remote__"

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
        message.pack()
        self.pipe.send(message)

    def dispatch_message(self, message):
        message.pack()
        self.pipe.send(message)

    def receive_message(self, message):
        self.receive_greeting(message)


class Referee (Actor):
    def __init__(self):
        Actor.__init__(self)

class Mailbox (object):

    def setup(self, world, actors):
        self.world = world
        self.actors = actors

    def update(self):
        raise NotImplementedError


class LocalMailbox (Mailbox):

    def setup(self, world, actors):
        Mailbox.setup(self, world, actors)
        self.id_factory = IdFactory(world)

    def update(self):

        packages = []

        for actor in self.actors:
            messages = actor.deliver_messages()
            packages += [ (actor, message) for message in messages ]

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
                private_message.set_origin(actor == sender)
                actor.dispatch_message(private_message)

            with UnprotectedProxyLock():
                message.execute(self.world)

            for actor in self.actors:
                private_message = message.copy()
                private_message.set_origin(actor == sender)
                with ProtectedProxyLock(actor):
                    actor.receive_message(private_message)


class RemoteMailbox (Mailbox):

    def __init__(self, pipe):
        self.pipe = pipe
        self.pipe.lock()

    def setup(self, world, actors):
        assert len(actors) == 1
        self.world = world
        self.actor = actors[0]

    def update(self):

        actor = self.actor
        ambassador = actor.ambassador

        for message in actor.deliver_messages():
            status = message.check(self.world, ambassador)

            if status:
                actor.accept_message(message, False)
            else:
                actor.reject_message(message)
                continue

            message.pack()
            self.pipe.send(message)

        self.pipe.deliver()

        for message in self.pipe.receive():
            message.unpack(self.world)

            if message.was_sent_from_here():
                if message.was_accepted():
                    actor.accept_message(message, True)
                else:
                    actor.reject_message(message)
                    continue

            with UnprotectedProxyLock():
                message.execute(self.world)

            with ProtectedProxyLock(actor):
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



def read_only(method):
    method.read_only = True
    return method


class Token (object):

    def __new__(cls, *args, **kwargs):

        token = object.__new__(cls, *args, **kwargs)
        token.__init__(*args, **kwargs)
        proxy = TokenProxy(token)

        return proxy

    def __init__(self, id):
        self.id = id

    def __extend__(self):
        return {}

    @read_only
    def get_id(self):
        return self.id


class World (Token):
    """ Everything in this class is duplicated in the Actor class.  I should
    have a generic base class that implements the setup/update/teardown
    functionality.  Of course, I'll have to think about ways to generalize that
    scheme first.  But it might be a good feature to stick into the base Engine
    class.   I also would like a way to avoid multiple inheritance. """

    def __init__(self):
        Token.__init__(self, 0)

    def setup(self):
        raise NotImplementedError

    def update(self, time):
        raise NotImplementedError

    def get_token(self, id):
        raise NotImplementedError


class TokenProxy (object):

    _access = 'unprotected'
    _actor = None

    def __init__(self, token):

        self._token = token
        self._extensions = {
                actor : extension_class(self)
                for actor, extension_class in token.__extend__().items() }

    def __getattr__(self, key):

        access = TokenProxy._access
        actor = TokenProxy._actor

        token = self._token
        extension = self._extensions.get(actor)

        if hasattr(token, key):
            member = getattr(token, key)

            if access == 'unprotected' or hasattr(member, 'read_only'):
                return member
            else:
                raise TokenPermissionError(key)

        elif extension and hasattr(extension, key):
            return getattr(extension, key)

        else:
            raise AttributeError(key)


class TokenPermissionError (Exception):
    pass

class TokenExtension (object):
    def __init__(self, token):
        pass

class ProxyLock:

    def __init__(self, access, actor=None):
        self.current_access = access
        self.current_actor = actor

    def __enter__(self):
        self.previous_access = TokenProxy._access
        self.previous_actor = TokenProxy._actor

        TokenProxy._access = self.current_access
        TokenProxy._actor = self.current_actor

    def __exit__(self, *args, **kwargs):
        TokenProxy._access = self.previous_access
        TokenProxy._actor = self.previous_actor

    @staticmethod
    def restrict_default_access():
        TokenProxy._access = 'protected'

    @staticmethod
    def allow_default_access():
        TokenProxy._access = 'unprotected'


class ProtectedProxyLock (ProxyLock):

    def __init__(self, actor):
        ProxyLock.__init__(self, 'protected', actor.get_name())


class UnprotectedProxyLock (ProxyLock):

    def __init__(self):
        ProxyLock.__init__(self, 'unprotected', None)



class Message (object):

    def check(self, world, sender):
        """ Returns true if the message is consistent with the state of the
        game world.  This method may be called several times on different
        hosts, and for that reason it is not able to modify the game world. """
        pass

    def update(self, actor, status):
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

    def pack(self):
        """ Modifies the message such that it can be faithfully pickled and
        sent over the network.  This primarily involves sending token ID
        numbers rather than tokens themselves. """

        packing_list = {}

        for name in dir(self):
            attribute = getattr(self, name)

            if isinstance(attribute, TokenProxy):
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


    def reject(self, actor):
        raise UnhandledMessageRejection(self)

    def accept(self, actor, pending):
        pass

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
