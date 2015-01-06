import collections
from .errors import *
from pprint import pprint

CallbackInfo = collections.namedtuple('CallbackInfo', 'message_cls, callback')

class ForumObserver:

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

    def react_to_message(self, message):
        self._call_callbacks('message', message)

    def react_to_soft_sync_error(self, message):
        self._call_callbacks('soft_sync_error', message)

    def react_to_hard_sync_error(self, message):
        self._call_callbacks('hard_sync_error', message)

    def _enable_forum_observation(self):
        self._is_enabled = True

    def _disable_forum_observation(self):
        self._is_enabled = False

    def _check_if_forum_observation_is_enabled(self):
        assert self._is_enabled, "{} has disabled forum observation.".format(self)

    def _add_callback(self, event, message_cls, callback):
        self._check_if_forum_observation_is_enabled()
        callback_info = CallbackInfo(message_cls, callback)
        self._callbacks[event].append(callback_info)

    def _drop_callback(self, event, message_cls, callback):
        self._check_if_forum_observation_is_enabled()

        # The [:] syntax is important, because it causes the same list object 
        # to be refilled with the new values.  Without it a new list would be 
        # created and the list in self.callbacks would not be changed.

        self._callbacks[event][:] = [
                callback_info for callback_info in self.callbacks[event]
                if (callback_info.message_cls is message_cls) and
                   (callback_info.callback is callback or callback is None)
        ]
        
    def _call_callbacks(self, event, message):
        self._check_if_forum_observation_is_enabled()

        # Call the callbacks stored in this observer.

        for callback_info in self._callbacks[event]:
            if isinstance(message, callback_info.message_cls):
                callback_info.callback(message)

        # Call the callbacks stored in nested observers.

        for observer in self._get_nested_observers():
            observer._call_callbacks(event, message)

    def _get_nested_observers(self):
        return []



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


