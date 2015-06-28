#!/usr/bin/env python3

from .errors import *
from .forums import ForumObserver

class Actor (ForumObserver):

    def __init__(self):
        super().__init__()
        self.world = None
        self._forum = None
        self._id_factory = None

    @property
    def id(self):
        assert self._id_factory is not None, "Actor does not have id."
        return self._id_factory.get()

    def is_referee(self):
        return isinstance(self, Referee)

    def send_message(self, message):
        # Indicate that the message was sent by this actor and give the message 
        # a chance to assign id numbers to the tokens it's creating.  This is 
        # done before the message is checked so that the check can make sure 
        # valid ids were assigned.

        message._set_sender_id(self._id_factory)
        message._assign_token_ids(self._id_factory)

        # Make sure that the message isn't requesting something that can't be 
        # done.  For example, make sure the players have enough resource when 
        # they're trying to buy things.  If the message fails the check, return 
        # False immediately.

        if not message._check(self.world, self._id_factory):
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

    def _set_world(self, world):
        assert self.world is None, "Actor already has world."
        self.world = world

    def _set_forum(self, forum, id_factory):
        assert self._id_factory is None, "Actor already has id."
        self._id_factory = id_factory

        assert self._forum is None, "Actor already has forum."
        self._forum = forum

    def _get_nested_observers(self):
        return (token.get_extension(self)
                for token in self.world if token.has_extension(self))

    def _dispatch_message(self, message):
        pass


class RemoteActor (Actor):

    def __init__(self, pipe):
        super().__init__()
        self._disable_forum_observation()
        self.pipe = pipe
        self.pipe.lock()

    def send_message(self):
        raise NotImplementedError

    def on_start_game(self):
        from .tokens import TokenSerializer
        serializer = TokenSerializer(self.world)
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
            
            if not message._check(self.world, self._id_factory):
                message._set_error_state(self.world)
                self.pipe.send(message)

                if message.has_hard_sync_error():
                    continue

            # Silently reject the message if it was sent by an actor with a 
            # different id that this one.  This should absolutely never happen 
            # because this actor gives its id to its client, so if a mismatch 
            # is detected we've mostly likely received some sort of malformed 
            # or malicious packet.

            if not message.was_sent_by(self._id_factory):
                continue

            # Execute the message if it hasn't been rejected yet.

            self._forum.dispatch_message(message)

        # Deliver any messages waiting to be sent.  This has to be done every 
        # frame because it sometimes takes more than one try to send a message.

        self.pipe.deliver()

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _set_forum(self, forum, id):
        super()._set_forum(forum, id)
        self.pipe.send(id)

    def _dispatch_message(self, message):
        if not message.was_sent_by(self._id_factory):
            self.pipe.send(message)
            self.pipe.deliver()

    def _react_to_message(self, message):
        """
        Don't ever change the world in response to a message.

        This method is defined is called by the game engine to trigger 
        callbacks tied by this actor to particular messages.  This is useful 
        for ordinary actors, but remote actors are only meant to shuttle 
        message between clients and should never react to individual messages.
        """
        pass


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
                raise UsingStaleReporter(message)
            else:
                self.referee.send_message(message)

    def on_update_game(self, dt):
        with Referee.Reporter(self) as reporter:
            for token in self.world:
                token.on_report_to_referee(reporter)

    def _set_forum(self, forum, id_factory):
        super()._set_forum(forum, id_factory)
        assert self.id == 1



@debug_only
def require_actor(object):
    require_instance(Actor(), object)

@debug_only
def require_actors(objects):
    for object in objects:
        require_actor(object)
