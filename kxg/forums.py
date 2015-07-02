#!/usr/bin/env python3

from .errors import *

class ForumObserver:

    from collections import namedtuple
    CallbackInfo = namedtuple('CallbackInfo', 'message_cls, callback')

    def __init__(self):
        super().__init__()

        # Create a data structure to hold all the callbacks registered with 
        # this observer.  Using a dictionary to distinguish between the regular 
        # message handlers, the soft sync error handlers, and the hard sync 
        # error handlers (instead of just having three different lists) makes 
        # it easy to write protected helpers to do most of the work.  

        self._callbacks = {
                'message': [],
                'soft_sync_error': [],
                'hard_sync_error': [],
        }

        # Create a member variable indicating whether or not the ability to 
        # subscribe to or unsubscribe from messages should be enabled.  Token 
        # disable this functionality until they've been added to the world and 
        # RemoteActors disable it permanently. 

        self._is_enabled = True

        # Decorators can be used to automatically label methods that should be 
        # callbacks.  Here, we look for methods that have been labeled in this 
        # way and register them appropriately.

        from inspect import getmembers, ismethod

        for method_name, method in getmembers(self, ismethod):
            message_cls = getattr(method, '_subscribe_to_message', None)
            if message_cls: self.subscribe_to_message(message_cls, method)

            message_cls = getattr(method, '_subscribe_to_soft_sync_error', None)
            if message_cls: self.subscribe_to_soft_sync_error(message_cls, method)

            message_cls = getattr(method, '_subscribe_to_hard_sync_error', None)
            if message_cls: self.subscribe_to_hard_sync_error(message_cls, method)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_callbacks']
        del state['_is_enabled']
        return state

    def __setstate__(self, state):
        ForumObserver.__init__(self)
        self.__dict__.update(state)

    def subscribe_to_message(self, message_cls, callback):
        self._add_callback('message', message_cls, callback)

    def subscribe_to_soft_sync_error(self, message_cls, callback):
        self._add_callback('soft_sync_error', message_cls, callback)

    def subscribe_to_hard_sync_error(self, message_cls, callback):
        self._add_callback('hard_sync_error', message_cls, callback)

    def unsubscribe_from_message(self, message_cls, callback=None):
        self._drop_callback('message', message_cls, callback)

    def unsubscribe_from_soft_sync_error(self, message_cls, callback=None):
        self._drop_callback('soft_sync_error', message_cls, callback)

    def unsubscribe_from_hard_sync_error(self, message_cls, callback=None):
        self._drop_callback('hard_sync_error', message_cls, callback)

    def _react_to_message(self, message):
        self._call_callbacks('message', message)

    def _react_to_soft_sync_error(self, message):
        self._call_callbacks('soft_sync_error', message)

    def _react_to_hard_sync_error(self, message):
        self._call_callbacks('hard_sync_error', message)

    def _enable_forum_observation(self):
        self._is_enabled = True

    def _disable_forum_observation(self):
        self._is_enabled = False

    def _check_if_forum_observation_enabled(self):
        assert self._is_enabled, "{} has disabled forum observation.".format(self)

    def _add_callback(self, event, message_cls, callback):
        self._check_if_forum_observation_enabled()
        callback_info = ForumObserver.CallbackInfo(message_cls, callback)
        self._callbacks[event].append(callback_info)

    def _drop_callback(self, event, message_cls, callback):
        self._check_if_forum_observation_enabled()

        # The [:] syntax is important, because it causes the same list object 
        # to be refilled with the new values.  Without it a new list would be 
        # created and the list in self.callbacks would not be changed.

        self._callbacks[event][:] = [
                callback_info for callback_info in self.callbacks[event]
                if (callback_info.message_cls is message_cls) and
                   (callback_info.callback is callback or callback is None)
        ]
        
    def _call_callbacks(self, event, message):
        self._check_if_forum_observation_enabled()

        # Call the callbacks stored in this observer.

        for callback_info in self._callbacks[event]:
            if isinstance(message, callback_info.message_cls):
                callback_info.callback(message)

        # Call the callbacks stored in nested observers.

        for observer in self._get_nested_observers():
            observer._call_callbacks(event, message)

    def _get_nested_observers(self):
        return []


class Forum:

    def __init__(self):
        self.world = None
        self.actors = None

    def dispatch_message(self, message):
        # Relay the messages to clients running on other machines, if this is a 
        # multiplayer game.  Since the tokens referenced in the message might 
        # be changed once the message is executed, the message has to be 
        # relayed before then.

        for actor in self.actors:
            actor._dispatch_message(message)

        # Normally, tokens can only call methods that have been decorated with 
        # @read_only.  This is a precaution to help keep the worlds in sync on 
        # all the clients.  This restriction is lifted when the tokens are 
        # handling messages and enforced again once the actors are handling 
        # messages.

        with self.world._unlock_temporarily():

            # First, let the message update the state of the game world.

            message._execute(self.world)

            # Second, let the world react to the message.  The main effect of 
            # the message should have already been carried out above.  These 
            # callbacks should take care of more peripheral effects.

            self.world._react_to_message(message)

        # Third, let the actors and the extensions react to the message.  This 
        # step is carried out last so that the actors can be sure that the 
        # world has a consistent state by the time their handlers are called.

        for actor in self.actors:
            actor._react_to_message(message)

    def connect_everyone(self, world, actors):
        # Save references to the world and the actors in the forum.

        self.world = world
        self.actors = actors

        # Save references to the actors in the world.  The world doesn't need 
        # to know about the forum because it can't send messages.  It needs to 
        # know about the actors so it can create token extensions.

        self.world._set_actors(actors)

        # Save references to the forum and the world in the actors.  Also 
        # assign each actor a factory it can use to generate unique token ids.
        #
        # In multiplayer games, each client needs the ability to create tokens, 
        # so that messages can be instantly handled.  Tokens still need unique 
        # ids though, so this method provides each actor with an IdFactory that 
        # generates ids using an offset and a spacing to ensure uniqueness.
        #
        # Actors take their own id numbers (used for figuring out who messages 
        # were sent by) from the offset parameter of the id factory.  Since the 
        # Referee must have an id of 0 if it's present, care is taken to make 
        # that happen.

        id_factories = self._assign_id_factories()

        for actor in self.actors:
            actor._set_world(world)
            actor._set_forum(self, id_factories[actor])

    def on_start_game(self):
        pass

    def on_update_game(self):
        # Forum doesn't do anything on a timer; it does everything in response 
        # to a message being sent.  But the RemoteForum uses this method to 
        # react to message that have arrived from the server.
        pass

    def on_finish_game(self):
        pass

    def _assign_id_factories(self):
        id_factories = {}
        actors = sorted(self.actors, key=lambda x: not x.is_referee())
        first_id = self.world.get_last_id() + 1
        spacing = len(self.actors)

        for offset, actor in enumerate(actors, first_id):
            id_factories[actor] = IdFactory(offset, spacing)

        return id_factories


class RemoteForum (Forum):

    def __init__(self, pipe):
        super().__init__()
        self.actor_id_factory = None
        self.pipe = pipe
        self.pipe.lock()

    def receive_id_from_server(self):
        """
        Listen for an id from the server.

        At the beginning of a game, each client receives an IdFactory from the 
        server.  This factory are used to give id numbers that are guaranteed 
        to be unique to tokens that created locally.  This method checks to see 
        if such a factory has been received  This method checks to see if such 
        a factory has been received.  If it hasn't, this method does not block 
        and immediately returns False.  If it has, this method returns True 
        after saving the factory internally.  At this point it is safe to enter 
        the GameStage.
        """
        for message in self.pipe.receive():
            if isinstance(message, IdFactory):
                self.actor_id_factory = message
                return True
        return False

    def dispatch_message(self, message):
        # Relay the message to a RemoteActor running on the server to update 
        # the world on all of the other machine playing the game as well.

        self.pipe.send(message)
        self.pipe.deliver()

        # Have the message update the local world like usual.

        super().dispatch_message(message)

    def dispatch_soft_sync_error(self, message):
        """
        Manage the response when the server reports a soft sync error.

        A soft sync error can happen when this client sends a message that 
        fails the check on the server.  If the reason for the failure isn't 
        very serious, then the server can decide to send it as usual in the 
        interest of a smooth gameplay experience.  When this happens, the 
        message is flagged as a soft sync error.

        The purpose of a soft sync error is to inform the clients that they 
        have become slightly out of sync with the server and to give them a 
        chance to get back in sync.  When a message is marked as a sync error, 
        it is also given the opportunity to save the information from the 
        server that would have prevented the error from occurring in the first 
        place.  Note that sync errors are only handled on clients.
        """

        # Synchronize the world.

        with self.world._unlock_temporarily():
            message._handle_soft_sync_error(self.world)
            self.world._react_to_soft_sync_error(message)

        # Synchronize the tokens.

        for actor in self.actors:
            actor._react_to_soft_sync_error(message)

    def dispatch_hard_sync_error(self, message):
        """
        Manage the response when the server reports a hard sync error.

        A hard sync error is produced when this client sends a message that the 
        server refuses to pass on to the other clients playing the game.  In 
        this case, the client must either undo the changes that the message 
        made to the world before being sent or crash.  Note that unlike a soft 
        sync error, a hard sync error is only reported to the client that sent 
        the offending message.
        """

        # Roll back changes that the original message made to the world.

        with self.world._unlock_temporarily():
            message._handle_hard_sync_error(self.world)
            self.world._react_to_hard_sync_error(message)

        # Give the actors a chance to react to the error.  For example, a 
        # GUI actor might inform the user that there are connectivity 
        # issues and that their last action was countermanded.

        for actor in self.actors:
            actor._react_to_hard_sync_error(message)

    def connect_everyone(self, world, actors):
        # Make sure that this forum is only connected to one actor.

        assert len(actors) == 1
        self.actor = actors[0]

        # Connect the forum, world, and actors as usual.

        super().connect_everyone(world, actors)

    def on_start_game(self):
        from .tokens import TokenSerializer
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self):
        # An attempt is made to immediately deliver any messages passed into 
        # relay_message(), but sometimes it takes more than one try to send a 
        # message.  So in case there are any messages waiting to be sent, the 
        # code below attempts to clear the queue every frame.

        self.pipe.deliver()

        # For each message received from the server:

        for message in self.pipe.receive():

            # Execute messages coming in from other clients.  Messages that are 
            # coming back in after being sent by this client have already been 
            # executed.  They are only being sent back because an error has 
            # been detected and needs to be handled.

            if not message.was_sent_by(self.actor_id_factory):
                super().dispatch_message(message)

            # If an incoming message has any error flags set, attempt to handle 
            # those as well.  A message coming from any client can have a soft 
            # sync error, but only messages that came from this client can have 
            # a hard sync error.

            if message.has_soft_sync_error():
                self.dispatch_soft_sync_error(message)

            if message.has_hard_sync_error():
                self.dispatch_hard_sync_error(message)

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _assign_id_factories(self):
        assert self.actor_id_factory is not None
        return {self.actor: self.actor_id_factory}


class IdFactory:

    def __init__(self, offset, spacing):
        self.offset = offset
        self.spacing = spacing
        self.num_ids_assigned = 0

    def __repr__(self):
        return 'IdFactory({}, {})'.format(self.offset, self.spacing)

    def __contains__(self, id):
        return id % self.spacing == self.offset % self.spacing

    def get(self):
        return self.offset

    def next(self):
        next_id = self.num_ids_assigned * self.spacing + self.offset
        self.num_ids_assigned += 1
        return next_id



@debug_only
def require_forum(object):
    require_instance(Forum(), object)

def subscribe_to_message(message_cls):
    def decorator(function):
        function._subscribe_to_message = message_cls
        return function
    return decorator

def subscribe_to_soft_sync_error(message_cls):
    def decorator(function):
        function._subscribe_to_soft_sync_error = message_cls
        return function
    return decorator

def subscribe_to_hard_sync_error(message_cls):
    def decorator(function):
        function._subscribe_to_hard_sync_error = message_cls
        return function
    return decorator

