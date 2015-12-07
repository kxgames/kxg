#!/usr/bin/env python3

from .errors import *
from .forums import ForumObserver

class Actor(ForumObserver):

    def __init__(self):
        super().__init__()
        self.world = None
        self._forum = None
        self._id_factory = None

    def __rshift__(self, message):
        return self.send_message(message)

    def send_message(self, message):
        info("sending a message: {message}")

        # Make sure the user didn't pass the wrong object to this function or 
        # forget to call the superclass constructor.

        from .messages import require_message
        require_message(message)

        # Make sure this message hasn't been sent more than once.  This is 
        # conceptually dangerous because messages can accumulate state as they 
        # are processed, and practically dangerous because it breaks the sent 
        # message cache in multiplayer games.

        if message.was_sent():
            raise CantReuseMessage()

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

        message._check(self.world)

        # Hand the message off to the forum to be applied to the world and 
        # relayed on to all the other actors (which may or may not be on 
        # different machines).

        self._forum.execute_message(message)
        return True

    @property
    def id(self):
        assert self._id_factory is not None, "Actor does not have id."
        return self._id_factory.get()

    def is_referee(self):
        return isinstance(self, Referee)

    def on_setup_gui(self, gui):
        pass

    def on_start_game(self, num_players):
        pass

    def on_update_game(self, dt):
        pass    # pragma: no cover

    def on_finish_game(self):
        pass

    def _set_world(self, world):
        assert self.world is None, "can't set world twice"
        self.world = world

    def _set_forum(self, forum, id_factory):
        assert self._id_factory is None, "Actor already has id."
        self._id_factory = id_factory

        assert self._forum is None, "Actor already has forum."
        self._forum = forum

    def _get_nested_observers(self):
        return (token.get_extension(self)
                for token in self.world if token.has_extension(self))

    def _relay_message(self, message):
        pass


class Referee(Actor):

    class Reporter:
        
        def __init__(self, referee):
            self.referee = referee
            self.is_finished_reporting = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.is_finished_reporting = True

        def __rshift__(self, message):
            return self.send_message(message)

        def send_message(self, message):
            if self.is_finished_reporting:
                raise UsingStaleReporter(message)
            else:
                return self.referee.send_message(message)

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
