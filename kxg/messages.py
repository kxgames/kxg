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
            raise MessageNotYetSent()

    def was_sent_by_referee(self):
        return self.was_sent_by(1)

    def tokens_to_add(self):
        yield from []

    def tokens_to_remove(self):
        yield from []

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
        raise UnhandledSyncError(self)

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
        # Called by Actor but not by ServerActor, so it is guaranteed to be 
        # called exactly once.  Not really different from the constructor, 
        # except that the id_factory object is nicely provided.  That's useful 
        # for adding tokens but probably nothing else.  This method is called 
        # before _check() so that _check() can make sure that valid ids were 
        # assigned.

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

        for token in self.tokens_to_remove():
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
            old_id = token.id
            token.reset_registration()
            token._id = old_id
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
        raise ObjectIsntMessageSubclass(cls)

