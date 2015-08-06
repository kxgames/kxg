#!/usr/bin/env python3

from .errors import *
from .tokens import require_token

# Message is still vulnerable because I could create a Message object, fill it 
# up with tokens, and send it.  The server would execute it no questions asked.  
# I need to add something somewhere that prevents unspecialized messages from 
# being executed.  
# 
# I could make on_check() etc. raise NotImplementerErrors.  That would make a 
# kind of sense.  It would make Message a little harder to subclass, but it's 
# probably the kind of thing every class should be doing anyway.  Should all 5 
# callbacks need to be reimplemented?  How about just on_check() and 
# on_execute()?  Would it be confusing to only have to reimplement two of the 
# five methods?  The real problem with this approach is that it will crash the 
# server if a bad message is received.

# It's not safe for any message class to have a list of tokens it's going to 
# add or remove from the world.  The reason is that it'd be very easy for a 
# cheater to retroactively instruct unrelated messages to add or remove tokens.  
# For example, a cheater could attach 1000 soldiers to a "build outpost" 
# message and as long as they can afford the outpost (because that's what the 
# message would check) they would also get the 1000 soldiers.  So this approach 
# is too vulnerable.
#
# Instead I need to make the user responsible for storing the tokens and just 
# provide methods that they can call in on_execute() and on_undo() that help 
# manage the tokens.  This makes it more explicit to the user what's going on.  
# If they call add_token() on something, they better have checked to make sure 
# that thing should be added.

# Message.on_check() should raise exceptions.

# Message.on_check() probably shouldn't take sender_id as an argument, because 
# the message should already know that about itself.

class Message:

    class ErrorState:
        SOFT_SYNC_ERROR = 0
        HARD_SYNC_ERROR = 1


    def __init__(self):
        super().__init__()
        self.tokens_to_add = []
        self.tokens_to_remove = []

    def __repr__(self):
        return self.__class__.__name__ + '()'

    def __getstate__(self):
        state = self.__dict__.copy()
        if not self.tokens_to_add: del state['tokens_to_add']
        if not self.tokens_to_remove: del state['tokens_to_remove']
        return state

    def __setstate__(self, state):
        Message.__init__(self)
        self.__dict__.update(state)
        self._was_sent = True

    def was_sent(self):
        return hasattr(self, 'sender_id')

    def was_sent_by(self, actor_or_id_factory):
        try: id = actor_or_id_factory.id
        except AttributeError: id = actor_or_id_factory.get()

        try: return self.sender_id == id
        except AttributeError: raise MessageNotYetSent()

    def was_sent_by_referee(self):
        try: return self.sender_id == 1
        except AttributeError: raise MessageNotYetSent()

    def add_token(self, token):
        require_token(token)
        if self.was_sent(): raise MessageAlreadySent()
        self.tokens_to_add.append(token)

    def add_tokens(self, tokens):
        if self.was_sent(): raise MessageAlreadySent()
        self.tokens_to_add.extend(tokens)

    def remove_token(self, token):
        require_token(token)
        if self.was_sent(): raise MessageAlreadySent()
        self.tokens_to_remove.append(token)

    def remove_tokens(self, tokens):
        if self.was_sent(): raise MessageAlreadySent()
        self.tokens_to_remove.extend(tokens)

    def on_check(self, world, sender_id):
        # Called by the actor.  Normal Actor will not send if this returns 
        # false.  ServerActor will decide if this is a hard or soft error.  It 
        # will relay soft errors but cancel hard errors.
        return True

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
        try: return self._server_response
        except AttributeError: return None

    def _assign_token_ids(self, id_factory):
        # Called by Actor but not by ServerActor, so it is guaranteed to be 
        # called exactly once.  Not really different from the constructor, 
        # except that the id_factory object is nicely provided.  That's useful 
        # for adding tokens but probably nothing else.  This method is called 
        # before _check() so that _check() can make sure that valid ids were 
        # assigned.

        for token in self.tokens_to_add:
            token._give_id(id_factory)

    def _check(self, world, id_factory):
        # Check all the tokens to create:

        for token in self.tokens_to_add:
            if token in world:
                return False

            # Make sure that the token was created by the same actor that's 
            # checking the message.

            if token.id not in id_factory:
                return False

        # Check all the tokens to destroy:

        for token in self.tokens_to_remove:
            if token not in world:
                return False

        # Let derived classes check themselves:

        return self.on_check(world, id_factory.get())

    def _prepare_sync(self, world, server_response):
        self._set_server_response(server_response)
        return self.on_prepare_sync(world, self._server_response)

    def _execute(self, world):
        # Deal with tokens to be created or destroyed.

        for token in self.tokens_to_add:
            world._add_token(token)

        for token in self.tokens_to_remove:
            world._remove_token(token)

        # Let derived classes execute themselves.

        self.on_execute(world)

    def _sync(self, world):
        self.on_sync(world, self._server_response)

    def _undo(self, world):
        # The tokens in self.tokens_to_add haven't been added to the world yet, 
        # because the message was copied and pickled before it was executed on 
        # the server.  We need to access the tokens that are actually in the 
        # world before we can remove them again.

        for token in self.tokens_to_add:
            real_token = world.get_token(token.id)
            world._remove_token(real_token)

        # The tokens in self.tokens_to_remove have already been removed from 
        # the world.  We want to add them back, and we want to make sure they 
        # end up with the id as before.

        for token in self.tokens_to_remove:
            old_id = token.id
            token.reset_registration()
            token._id = old_id
            world._add_token(token)

        # Let derived classes execute themselves.

        self.on_undo(world)



@debug_only
def require_message(object):
    require_instance(Message(), object)

@debug_only
def require_message_cls(cls):
    if not isinstance(cls, type) or not issubclass(cls, Message):
        raise ObjectIsntMessageSubclass(cls)

