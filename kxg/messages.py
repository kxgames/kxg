#!/usr/bin/env python3

from .errors import *

class Message:
    # This class defers initializing all of its members until the appropriate 
    # setter is called, rather than initializing everything in a constructor.  
    # This is done to avoid sending unnecessary information over the network.

    class ErrorState:
        SOFT_SYNC_ERROR = 0
        HARD_SYNC_ERROR = 1


    def __repr__(self):
        return self.__class__.__name__ + '()'

    def was_sent(self):
        return hasattr(self, 'sender_id')

    def was_sent_by(self, actor_or_id):
        from .actors import Actor
        from .forums import IdFactory

        if isinstance(actor_or_id, Actor):
            id = actor_or_id.id
        elif isinstance(actor_or_id, IdFactory):
            id = actor_or_id.get()
        else:
            id = actor_or_id

        try:
            return self.sender_id == id
        except AttributeError:
            raise ApiUsageError("""\
                    Can't ask who sent a message before it's been sent.

                    This error means Message.was_sent_by() or 
                    Message.was_sent_by_referee() got called on a message that 
                    hadn't been sent yet.  Normally you would only call these 
                    methods from within Message.on_check().""")

    def was_sent_by_referee(self):
        return self.was_sent_by(1)

    def tokens_to_add(self):
        yield from []

    def tokens_to_remove(self):
        yield from []

    def tokens_referenced(self):
        """
        Return a list of all the tokens that are referenced (i.e. contained in) 
        this message.  Tokens that haven't been assigned an id yet are searched 
        recursively for tokens.  So this method may return fewer results after 
        the message is sent.  This information is used by the game engine to 
        catch mistakes like forgetting to add a token to the world or keeping a 
        stale reference to a token after its been removed.
        """
        tokens = set()

        # Use the pickle machinery to find all the tokens contained at any 
        # level of this message.  When an object is being pickled, the Pickler 
        # calls its persistent_id() method for each object it encounters.  We  
        # hijack this method to add every Token we encounter to a list.

        # This definitely feels like a hacky abuse of the pickle machinery, but 
        # that notwithstanding this should be quite robust and quite fast.

        def persistent_id(obj):
            from .tokens import Token

            if isinstance(obj, Token):
                tokens.add(obj)

                # Recursively descend into tokens that haven't been assigned an 
                # id yet, but not into tokens that have.

                return obj.id

        from pickle import Pickler
        from io import BytesIO

        # Use BytesIO to basically ignore the serialized data stream, since we 
        # only care about visiting all the objects that would be pickled.

        pickler = Pickler(BytesIO())
        pickler.persistent_id = persistent_id
        pickler.dump(self)

        return tokens

    def on_check(self, world):
        # Called by the actor.  If no MessageCheck exception is raised, the 
        # message will be sent as usual.  Otherwise, the behavior will depend 
        # on what kind of actor is handling the message.  Actor (uniplayer and 
        # multiplayer clients) will Normal Actor will simply not send the 
        # message.  ServerActor (multiplayer server) will decide if the error 
        # should be handled by undoing the message or asking the clients to 
        # sync themselves.
        raise NotImplementedError

    def on_prepare_sync(self, world, memento):
        # Called only by ServerActor if on_check() returns False.  If this 
        # method returns True, the message will be relayed to the rest of the 
        # clients with the sync error flag set.  Otherwise the message will not 
        # be sent and the ClientForum that sent the message will be instructed 
        # to undo it.  If a soft error is detected, this method should save 
        # information about the world that it could use to resynchronize all 
        # the clients.
        return False

    def on_execute(self, world):
        # Called by the forum on every machine running the game.  Allowed to 
        # make changes to the game world, but should not change the message 
        # itself.  Called before any signal-handling callbacks.
        pass

    def on_sync(self, world, memento):
        # Called by the forum upon receiving a message with the soft error flag 
        # set.  This flag indicates that the client that sent the message is 
        # slightly out of sync with the server, but that the message will be 
        # relayed as usual and that the clients should use the opportunity to 
        # quietly resynchronize themselves.  
        pass

    def on_undo(self, world):
        # Called by ClientForum only upon receiving a message with the hard 
        # error flag set.  This flag indicates that the server refused to relay 
        # the given message to the other clients, presumably because it was too 
        # far out of sync with the world on the server, and that the message 
        # needs to be undone on this client.  Only the ClientForum that sent 
        # the offending message will call this method.
        message_cls = self.__class__.__name__
        raise ApiUsageError("""\
                The message {self} was rejected by the server.

                This client attempted to send a {message_cls} message, but it 
                was rejected by the server.  To fix this error, either figure 
                out why the client is getting out of sync with the server or 
                implement a {message_cls}.on_undo() that undoes everything done 
                in {message_cls}.on_execute().""")

    def _set_sender_id(self, id_factory):
        self.sender_id = id_factory.get()

    def _set_server_response_id(self, id):
        self._server_response_id = id

    def _get_server_response_id(self):
        return self._server_response_id

    def _set_server_response(self, server_response):
        self._server_response = server_response

    def _get_server_response(self):
        try:
            return self._server_response
        except AttributeError:
            return None

    def _assign_token_ids(self, id_factory):
        """
        Assign id numbers to any tokens that will be added to the world by this 
        message.

        This method is called by Actor but not by ServerActor, so it's 
        guaranteed to be called exactly once.  In fact, this method is not 
        really different from the constructor, except that the id_factory 
        object is nicely provided.  That's useful for assigning ids to tokens 
        but probably nothing else.  This method is called before _check() so 
        that _check() can make sure that valid ids were assigned (although by 
        default it doesn't).
        """
        for token in self.tokens_to_add():
            token._give_id(id_factory)

    def _check(self, world):
        self.on_check(world)

    def _prepare_sync(self, world, server_response):
        self._set_server_response(server_response)
        return self.on_prepare_sync(world, self._server_response)

    def _execute(self, world):
        # Deal with tokens to be created or destroyed.

        for token in self.tokens_to_add():
            world._add_token(token)

        # Save the id numbers for the tokens we're removing so we can restore 
        # them if we need to undo this message.

        self._removed_token_ids = {}
        for token in self.tokens_to_remove():
            self._removed_token_ids[token] = token.id
            world._remove_token(token)

        # Let derived classes execute themselves.

        self.on_execute(world)

    def _sync(self, world):
        self.on_sync(world, self._server_response)

    def _undo(self, world):
        # The tokens in self.tokens_to_add() haven't been added to the world 
        # yet, because the message was copied and pickled before it was 
        # executed on the server.  We need to access the tokens that are 
        # actually in the world before we can remove them again.

        for token in self.tokens_to_add():
            real_token = world.get_token(token.id)
            world._remove_token(real_token)

        # The tokens in self.tokens_to_remove() have already been removed from 
        # the world.  We want to add them back, and we want to make sure they 
        # end up with the id as before.

        for token in self.tokens_to_remove():
            token._id = self._removed_token_ids[token]
            world._add_token(token)

        # Let derived classes execute themselves.

        self.on_undo(world)


class MessageCheck(Exception):
    pass


@debug_only
def require_message(object):
    require_instance(Message(), object)

@debug_only
def require_message_cls(cls):
    if not isinstance(cls, type) or not issubclass(cls, Message):
        try: wrong_thing = cls.__name__
        except: wrong_thing = cls
        raise ApiUsageError("""\
                expected Message subclass, but got {wrong_thing} instead.""")

