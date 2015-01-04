import contextlib
from . import errors

class Message:

    class ErrorState:
        SOFT_SYNC_ERROR = 0
        HARD_SYNC_ERROR = 1


    def __new__(cls, *args, **kwargs):
        # There are two things about this method that are a little tricky.  The 
        # first is that I decided to implement __new__() instead of __init__() 
        # so that the user wouldn't have to remember to call __init__().  The 
        # reason is that the locking system generates really weird errors if it 
        # isn't set up properly, so I wanted to prevent that from happening.  
        #
        # The second tricky thing is how the locking system gets set up.  The 
        # system revolves around a member variable named _mutable.  If _mutable 
        # is defined, attributes can be set; otherwise they can't.  The system 
        # works like this so that by the time the message is sent over the 
        # network, the message has been locked and _mutable has been unset, so 
        # the extra boolean field doesn't need to be set over the network.  
        # However, a little trickiness is required to set the _mutable member 
        # in the first place.  That what the __dict__ assignment below does.
   
        message = super().__new__(cls)
        message.__dict__['_mutable'] = True
        return message

    def __setattr__(self, key, value):
        if hasattr(self, '_mutable'):
            super().__setattr__(key, value)
        else:
            raise errors.ImmutableMessageError(self)

    def get_messages(self):
        return [self]

    def set_sender_id(self, sender_id):
        self.sender_id = sender_id.get()

    def was_sent_by(self, sender_id):
        return self.sender_id == sender_id.get()

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

    def lock(self):
        del self._mutable

    def copy(self):
        """
        Return a shallow copy of the message object.
        
        This is called by the game engine just before the message is delivered 
        to the actors, so that the game can provide information specific to 
        certain actors.
        """
        import copy
        return copy.copy(self)


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
        raise errors.UnhandledSyncError


class CompositeMessage(Message):

    def __init__(self, *messages):
        super().__init__()
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



