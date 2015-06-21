#!/usr/bin/env python3

from .errors import *

class Message:

    class ErrorState:
        SOFT_SYNC_ERROR = 0
        HARD_SYNC_ERROR = 1


    def set_sender_id(self, sender_id):
        self.sender_id = sender_id.get()

    def was_sent_by(self, sender_id):
        return self.sender_id == sender_id.get()

    def was_sent_by_referee(self):
        return self.sender_id == 0

    def set_error_state(self, world):
        if self.on_check_for_soft_sync_error(world):
            self._error_state = Message.ErrorState.SOFT_SYNC_ERROR
        else:
            self._error_state = Message.ErrorState.HARD_SYNC_ERROR

    def has_soft_sync_error(self):
        return getattr(self, '_error_state', None) == Message.ErrorState.SOFT_SYNC_ERROR

    def has_hard_sync_error(self):
        return getattr(self, '_error_state', None) == Message.ErrorState.HARD_SYNC_ERROR

    def get_tokens_to_create(self):
        return []

    def get_tokens_to_destroy(self):
        return []

    def copy(self):
        """
        Return a shallow copy of the message object.
        
        This is called by the game engine just before the message is delivered 
        to the actors, so that the game can provide information specific to 
        certain actors.
        """
        import copy
        return copy.copy(self)


    def assign_token_ids(self, id_factory):
        # Called by Actor but not by RemoteActor, so it is guaranteed to be 
        # called exactly once.  Not really different from the constructor, 
        # except that the id_factory object is nicely provided.  That's useful 
        # for CreateToken but probably nothing else.  Could be called after 
        # check() to not waste id numbers, but that's not super important.

        for token in self.get_tokens_to_create():
            token.give_id(id_factory)

    def check(self, world, id_factory):
        # Check all the tokens to create:

        for token in self.get_tokens_to_create():
            if token in world:
                return False

            # Make sure that the token was created by the same actor that's 
            # checking the message.

            if token.id not in id_factory:
                return False

        # Check all the tokens to destroy:
        
        for token in self.get_tokens_to_destroy():
            if token not in world:
                return False

        # Let derived classes check themselves:

        return self.on_check(world, id_factory.get())

    def execute(self, world):
        # Deal with tokens to be created or destroyed.

        for token in self.get_tokens_to_create():
            world._add_token(token)

        for token in self.get_tokens_to_destroy():
            world._remove_token(token)

        # Let derived classes execute themselves.

        self.on_execute(world)

    def handle_soft_sync_error(self, world):
        self.on_soft_sync_error(world)

    def handle_hard_sync_error(self, world):
        # Deal with the tokens that were created or destroyed.

        for token in self.get_tokens_to_create():
            world._remove_token(token)

        for token in self.get_tokens_to_destroy():
            world._add_token(token)

        # Let derived classes execute themselves.

        self.on_hard_sync_error(world)


    def on_check(self, world, sender_id):
        # Called by the actor.  Normal Actor will not send if this returns 
        # false.  RemoteActor will decide if this is a hard or soft error.  It 
        # will relay soft errors but cancel hard errors.
        return True

    def on_check_for_soft_sync_error(self, world):
        # Called only by RemoteActor if check() returns False.  If this method 
        # returns True, the message will be relayed to the rest of the clients 
        # with the sync error flag set.  Otherwise the message will not be sent 
        # and the RemoteForum that sent the message will be instructed to undo 
        # it.  If a soft error is detected, this method should save information 
        # about the world that it could use to resynchronize all the clients.
        return False

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
        raise UnhandledSyncError(self)


class CreateToken (Message):

    def __init__(self, token):
        self.token = token

    def get_tokens_to_create(self):
        return [self.token]


class CreateTokens (Message):

    def __init__(self, tokens):
        self.tokens = tokens

    def get_tokens_to_create(self):
        return self.tokens


class DestroyToken (Message):

    def __init__(self, token):
        self.token = token

    def get_tokens_to_destroy(self):
        return [self.token]


class DestroyTokens (Message):

    def __init__(self, tokens):
        self.tokens = tokens

    def get_tokens_to_destroy(self):
        return self.tokens


