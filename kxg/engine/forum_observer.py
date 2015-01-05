import collections
from .errors import *
from pprint import pprint

CallbackInfo = collections.namedtuple('CallbackInfo', 'message_cls, callback')

class ForumObserver:

    # Classes that inherit from ForumObserver must call _configure_observer() 
    # before subscribing to any messages.

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

    def _configure_observer(self):
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

    def _require_active_observer(self):
        assert hasattr(self, '_callbacks'), "ForumObserver not yet configured."
        assert self._is_observation_allowed(), "Cannot observe messages from {}".format(self)

    def _add_callback(self, event, message_cls, callback):
        self._require_active_observer()
        callback_info = CallbackInfo(message_cls, callback)
        self._callbacks[event].append(callback_info)

    def _drop_callback(self, event, message_cls, callback):
        self._require_active_observer()

        # The [:] syntax is important, because it causes the same list object 
        # to be refilled with the new values.  Without it a new list would be 
        # created and the list in self.callbacks would not be changed.

        self._callbacks[event][:] = [
                callback_info for callback_info in self.callbacks[event]
                if (callback_info.message_cls is message_cls) and
                   (callback_info.callback is callback or callback is None)
        ]
        
    def _call_callbacks(self, event, message):
        print ('cc', self)
        self._require_active_observer()

        # Call the callbacks stored in this observer.

        for callback_info in self._callbacks[event]:
            if isinstance(message, callback_info.message_cls):
                callback_info.callback(message)

        # Call the callbacks stored in nested observers.

        for observer in self._get_nested_observers():
            observer._call_callbacks(event, message)

    def _get_nested_observers(self):
        return []

    def _is_observation_allowed(self):
        return True



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


