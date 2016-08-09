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
        info("sending message: {message}")

        # Make sure the user didn't pass the wrong object to this function or 
        # forget to call the superclass constructor.

        from .messages import require_message
        require_message(message)

        # Make sure this message hasn't been sent more than once.  This is 
        # conceptually dangerous because messages can accumulate state as they 
        # are processed, and practically dangerous because it breaks the "sent 
        # message cache" in multiplayer games.

        if message.was_sent():
            raise ApiUsageError("""\
                    {message} has already been sent.

                    It's not safe to send the same message twice because 
                    messages can accumulate state as they are executed.  
                    Duplicate messages would also break the system by which 
                    clients react to responses from the server in multiplayer 
                    games.""")

        # Make sure that every token referenced in this message (i.e. every 
        # token that would get pickled when this message is sent over the 
        # network) is either in or not in the world, whichever is expected:
        # 
        # - Tokens that are being added to the world are expected to not 
        #   already be in it.
        #
        # - Any other token is expected to be in the world.
        # 
        # These expectations can sometimes be broken by relatively innocuous 
        # misuses of the game engine, so it's useful to have these checks.

        for token in message.tokens_referenced():
            if token not in self.world and token not in message.tokens_to_add():
                raise ApiUsageError("""\
                        {token} was referenced by {message} despite not 
                        being in the world.

                        Every token referenced by a message, except those being 
                        added to the world, must be in the world.  This is 
                        mostly a sanity check: a token that's not in the world 
                        shouldn't be in a message because it shouldn't be 
                        participating in the game at all!  But this is also a 
                        synchronization issue for multiplayer games: there's no 
                        way to communicate over the network about a token that 
                        doesn't have an established id.

                        There are several common ways to get this error:  

                        1. Using a token that was previously removed from the 
                           world.  This can happen if a token is removed from 
                           the world but not from all the lists it was a part 
                           of, for example.  

                        2. Forgetting to yield a token from tokens_to_add().  
                           Even tokens that are nested in other tokens need to 
                           be yielded by this method to be added to the world.

                        3. Using a token that was never added to the world.  
                           This can happen is you put a token in the world 
                           without using a message to do it.""")

        for token in message.tokens_to_add():
            if token in self.world:
                raise ApiUsageError("""\
                        can't add {token} to the world twice.

                        {token} was referenced by tokens_to_add(), but it can't 
                        be added to the world because it's already in it.""")

        for token in message.tokens_to_remove():
            if token not in self.world:
                raise ApiUsageError("""\
                        can't remove {token} from the world twice.

                        {token} was referenced by tokens_to_remove(), but it 
                        can't be removed from the world because it's not in 
                        it.  This usually means {token} is being removed for a 
                        second time, perhaps due to a stale reference, but it 
                        could also mean {token} was never added to the world in 
                        the first place.""")

        # Indicate that the message was sent by this actor and give the message 
        # a chance to assign id numbers to the tokens it's creating.  This is 
        # done before the message is checked so that the check can make sure 
        # valid ids were assigned.

        message._set_sender_id(self._id_factory)
        message._assign_token_ids(self._id_factory)

        # Make sure that the message isn't requesting something that can't be 
        # done.  For example, make sure the players have enough resource when 
        # they're trying to buy things.  If the message fails the check, an 
        # exception will be raised.

        message._check(self.world)

        # Hand the message off to the forum to be applied to the world and 
        # relayed on to all the other actors (which may or may not be on 
        # different machines).

        self._forum.execute_message(message)

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
                raise ApiUsageError("""\
                        {message.__class__.__name__} message sent using a stale 
                        reporter.

                        This message is raised when the reporter provided to 
                        Token.report() is used after that method returns.  This 
                        can only happen if you save a reference to the 
                        reporter, which you shouldn't do.  This is a 
                        multiplayer synchronization issue.  Because the same 
                        token should exist in the same state on every machine 
                        playing the game, tokens normally can't send messages 
                        or they would be prone to sending duplicate messages.  
                        The exception is Token.report(), which is guaranteed to 
                        be called only on the server.  Token.report() is 
                        provided with a reporter object that can be used to 
                        send messages, but it's illegal to save a reference to 
                        the reporter and use it after Token.report() returns.  
                        Such a design would lead to bugs on the clients, which 
                        are never given reporter objects.""")
            else:
                return self.referee.send_message(message)

    def on_update_game(self, dt):
        with Referee.Reporter(self) as reporter:
            self.world.on_report_to_referee(reporter)
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
