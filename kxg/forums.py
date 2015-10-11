#!/usr/bin/env python3

from .errors import *

class Forum:

    def __init__(self):
        self.world = None
        self.actors = None

    def execute_message(self, message):
        info("executing a message: {message}")

        # Relay the messages to clients running on other machines, if this is a 
        # multiplayer game.  Since the tokens referenced in the message might 
        # be changed once the message is executed, the message has to be 
        # relayed before then.

        for actor in self.actors:
            actor._relay_message(message)

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
        # to a message being sent.  But the ClientForum uses this method to 
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
                'sync_response': [],
                'undo_response': [],
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

        for _, method in getmembers(self, ismethod):
            for message_cls in getattr(method, '_kxg_subscribe_to_message', []):
                self.subscribe_to_message(message_cls, method)

            for message_cls in getattr(method, '_kxg_subscribe_to_sync_response', []):
                self.subscribe_to_sync_response(message_cls, method)

            for message_cls in getattr(method, '_kxg_subscribe_to_undo_response', []):
                self.subscribe_to_undo_response(message_cls, method)

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

    def subscribe_to_sync_response(self, message_cls, callback):
        self._add_callback('sync_response', message_cls, callback)

    def subscribe_to_undo_response(self, message_cls, callback):
        self._add_callback('undo_response', message_cls, callback)

    def unsubscribe_from_message(self, message_cls, callback=None):
        self._drop_callback('message', message_cls, callback)

    def unsubscribe_from_sync_response(self, message_cls, callback=None):
        self._drop_callback('sync_response', message_cls, callback)

    def unsubscribe_from_undo_response(self, message_cls, callback=None):
        self._drop_callback('undo_response', message_cls, callback)

    def _react_to_message(self, message):
        self._call_callbacks('message', message)

    def _react_to_sync_response(self, message):
        self._call_callbacks('sync_response', message)

    def _react_to_undo_response(self, message):
        self._call_callbacks('undo_response', message)

    def _enable_forum_observation(self):
        self._is_enabled = True

    def _disable_forum_observation(self):
        self._is_enabled = False

    def _check_if_forum_observation_enabled(self):
        assert self._is_enabled, "{} has disabled forum observation.".format(self)

    def _add_callback(self, event, message_cls, callback):
        from .messages import require_message_cls
        require_message_cls(message_cls)
        self._check_if_forum_observation_enabled()
        callback_info = ForumObserver.CallbackInfo(message_cls, callback)
        self._callbacks[event].append(callback_info)

    def _drop_callback(self, event, message_cls, callback):
        from .messages import require_message_cls
        require_message_cls(message_cls)
        self._check_if_forum_observation_enabled()
        self._callbacks[event] = [
                x for x in self._callbacks[event]
                if not ((x.message_cls is message_cls) and
                        (x.callback is callback or callback is None)
                )
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


class IdFactory:

    def __init__(self, offset, spacing):
        self.offset = offset
        self.spacing = spacing
        self.num_ids_assigned = 0

    def __repr__(self):
        return 'IdFactory(offset={}, spacing={})'.format(
                self.offset, self.spacing)

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
        try:
            function._kxg_subscribe_to_message.append(message_cls)
        except AttributeError:
            function._kxg_subscribe_to_message = [message_cls]
        return function
    return decorator

def subscribe_to_sync_response(message_cls):
    def decorator(function):
        try:
            function._kxg_subscribe_to_sync_response.append(message_cls)
        except AttributeError:
            function._kxg_subscribe_to_sync_response = [message_cls]
        return function
    return decorator

def subscribe_to_undo_response(message_cls):
    def decorator(function):
        try:
            function._kxg_subscribe_to_undo_response.append(message_cls)
        except AttributeError:
            function._kxg_subscribe_to_undo_response = [message_cls]
        return function
    return decorator


