#!/usr/bin/env python3

from .errors import *
from .forums import ForumObserver
from .actors import require_actor

def read_only(method):
    setattr(method, '_kxg_read_only', True)
    return method

def before_world(method):
    setattr(method, '_kxg_before_world', True)
    return method

def watch_token(method):
    """
    Mark a token extension method that should automatically be called when a 
    token method of the same name is called.

    This decorator must only be used on TokenExtension methods, otherwise it 
    will silently do nothing.  The reason is that the decorator itself can't do 
    anything but label the given method, because at the time of decoration the 
    token to watch isn't known.  The method is actually setup to watch a token 
    in the TokenExtension constructor, which searches for the label added here.  
    But other classes won't make this search and will silently do nothing.
    """
    method._kxg_watch_token = True
    return method

@debug_only
def require_token(object):
    return require_instance(Token(), object)

@debug_only
def require_active_token(object):
    token = require_token(object)

    if token.world_registration == 'pending':
        if not token.has_id():
            raise TokenDoesntHaveId(token)
        if not token.has_world():
            raise TokenNotInWorld(token)
    if token.world_registration == 'expired':
        raise UsingRemovedToken(token)

    return token


class TokenMetaclass(type):

    def __new__(mcs, name, bases, members):
        """
        Add checks to make sure token methods are being called safely.

        In order to keep multiplayer games in sync, the world should only be 
        modified at particular times (e.g. token update methods and messages).  
        The purpose of this metaclass is to stop you from accidentally trying 
        to modify the world outside of these defined times.  These mistakes 
        would otherwise cause hard-to-debug sync errors.

        The engine indicates when it is safe to modify the world by setting a 
        boolean lock flag in the world.  This metaclass adds a bit of logic to 
        non-read-only token methods that makes sure the world is unlocked 
        before continuing.  The kxg.read_only() decorator can be used to 
        indicate which methods are read-only, and are therefore excluded from 
        these checks.
        
        The checks configured by this metaclass help find bugs, but may also 
        incur significant computational expense.  By invoking python with 
        optimization enabled (i.e. passing -O) these checks are skipped.
        """

        if __debug__:
            mcs.add_safety_checks(members)

        return super().__new__(mcs, name, bases, members)
        

    @classmethod
    def add_safety_checks(mcs, members):
        """
        Iterate through each member of the class being created and add a 
        safety check to every method that isn't marked as read-only.
        """
        for member_name, member_value in members.items():
            members[member_name] = mcs.add_safety_check(
                    member_name, member_value)

    @staticmethod
    def add_safety_check(member_name, member_value):
        """
        If the given member is a method that hasn't been marked as read-only, 
        return a version of it that will complain if invoked in a dangerous 
        way.  This mostly means checking to make sure that methods that alter 
        the token are only called from update methods or messages.
        """

        import functools
        from types import FunctionType

        is_method = isinstance(member_value, FunctionType)
        is_read_only = hasattr(member_value, '_kxg_read_only')
        is_engine_helper = member_name.startswith('_')

        if not is_method or is_read_only or is_engine_helper:
            return member_value

        def safety_checked_method(self, *args, **kwargs):

            if self.world_registration == 'pending':

                # Calling a non-read-only method before on a token before 
                # adding it to the world isn't inherently a synchronization 
                # issue, because until a token is added to the world only 
                # one client knows about it.  However, this happens most 
                # often when the user forgets to add a token to the world 
                # in the first place.  To catch these bugs, non-read-only 
                # token methods can't be called before the token has been 
                # added to the world unless they are explicitly labeled 
                # with the kxg.before_world() decorator.

                if not hasattr(member_value, '_kxg_before_world'):
                    raise CantModifyTokenIfNotInWorld(self, member_name)

            if self.world_registration == 'active':

                # If the token has already been added to the world, make 
                # sure that the token seems properly set up (specifically 
                # that it has all the attributes that tokens should have 
                # and that it's id isn't null) and that the world is 
                # unlocked.

                require_active_token(self)

                if self.world.is_locked():
                    raise CantModifyTokenIfWorldLocked(self, member_name)

            if self.world_registration == 'expired':

                # Once a token has been removed from the world, almost 
                # anything you do with it will raise an exception.  This 
                # behavior is meant to prevent bugs that happen when you 
                # accidentally keep stale references to removed tokens.  If 
                # you need to add a removed token again, you can call its 
                # reset_registration() method, which will allow you to add 
                # it to the world again in the usual way (i.e. by sending a 
                # message).

                if member_name != 'reset_registration':
                    raise UsingRemovedToken(self)

            # After all the checks have been carried out, call the method 
            # as usual.

            return member_value(self, *args, **kwargs)

        # Preserve any "forum observer" decorations that have been placed on 
        # the method.  Also restore the method's original name and module 
        # strings, to make inspection and debugging a little easier.

        functools.update_wrapper(
                safety_checked_method, member_value,
                assigned=functools.WRAPPER_ASSIGNMENTS + (
                    '_kxg_subscribe_to_message',
                    '_kxg_subscribe_to_sync_response',
                    '_kxg_subscribe_to_undo_response',
                )
        )
        return safety_checked_method

        

class Token(ForumObserver, metaclass=TokenMetaclass):

    class WatchedMethod:

        def __init__(self, method):
            self.method = method
            self.watchers = []

        def __call__(self, *args, **kwargs):
            self.method(*args, **kwargs)
            for watcher in self.watchers:
                watcher(*args, **kwargs)

        def add_watcher(self, watcher):
            self.watchers.append(watcher)


    def __init__(self):
        super().__init__()
        self._id = None
        self._world = None
        self._removed_from_world = False
        self._extensions = {}
        self._disable_forum_observation()

    def __repr__(self):
        return '{}(id={})'.format(
                self.__class__.__name__, getattr(self, 'id', None))

    def __getstate__(self):
        state = super().__getstate__()
        del state['_world']
        del state['_removed_from_world']
        del state['_extensions']
        return state

    def __setstate__(self, state):
        Token.__init__(self)
        super().__setstate__(state)

    def __extend__(self):
        return {}

    @property
    @read_only
    def id(self):
        return self._id

    @property
    @read_only
    def world(self):
        return self._world

    @property
    @read_only
    def world_registration(self):
        """
        Return the status of this token's registration with the world.

        There are three possible world registration statuses.  The first is 
        'pending', which means that the token has not yet been added to the 
        world (although it may have been assigned an id).  The second is 
        'active', which means that the token is fully participating in the 
        game.  The third is 'expired', which means that the token has been 
        removed from the world and should no longer be in use.  These statuses 
        are mostly used for internal checks within the game engine.
        """
        if self._removed_from_world:
            return 'expired'
        elif self.has_world():
            if not self.has_id():
                raise TokenDoesntHaveId(self)
            return 'active'
        else:
            return 'pending'

    @read_only
    def has_id(self):
        return self.id is not None

    @read_only
    def has_world(self):
        assert (not self.world) or (self in self.world)
        return self.world is not None

    @read_only
    def has_extension(self, actor):
        require_actor(actor)
        return actor in self._extensions

    @read_only
    def get_extension(self, actor):
        require_actor(actor)
        return self._extensions[actor]

    @read_only
    def get_extensions(self):
        return list(self._extensions.values())

    @read_only
    def watch_method(self, method_name, callback):
        """
        Register the given callback to be called whenever the method with the 
        given name is called.  You can easily take advantage of this feature in 
        token extensions by using the @watch_token decorator.
        """

        # Make sure a token method with the given name exists, and complain if 
        # nothing is found.

        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise TokenHasNoSuchMethodToWatch(self, method_name)

        # Wrap the method in a WatchedMethod object, if that hasn't already 
        # been done.  This object manages a list of callback method and takes 
        # responsibility for calling them after the method itself has been 
        # called.

        if not isinstance(method, Token.WatchedMethod):
            setattr(self, method_name, Token.WatchedMethod(method))
            method = getattr(self, method_name)

        # Add the given callback to the watched method.

        method.add_watcher(callback)

    @read_only
    def reset_registration(self):
        """
        Allow the token to be added to the world again.

        Once a token has been removed from the world, almost anything you do 
        with it will raise an exception.  This behavior is meant to prevent 
        bugs that happen when you accidentally keep stale references to removed 
        tokens.  Calling this method circumvents those checks behavior and 
        allows you to add a removed token back into the world.  Note that this 
        method does not actually add the token to the world, it just allows you 
        to do that in the usual way (i.e. by sending a message).  
        """
        if self.world_registration != 'expired':
            raise CantResetActiveToken(self)
        Token.__init__(self)

    def on_add_to_world(self, world):
        pass

    def on_update_game(self, dt):
        pass

    @read_only
    def on_report_to_referee(self, reporter):
        pass

    def on_remove_from_world(self):
        pass

    def _give_id(self, id_factory):
        from .forums import IdFactory

        require_token(self)

        if self.has_id():
            raise TokenAlreadyHasId(self)
        if not isinstance(id_factory, IdFactory):
            raise NotUsingIdFactory(id_factory)

        self._id = id_factory.next()

    def _check_if_forum_observation_enabled(self):
        """
        Give a helpful error if the user attempts to subscribe or unsubscribe 
        from messages while the token is not registered with a world.  This can 
        easily happen if the user attempts to subscribe to messages in the 
        constructor.  However, because the constructor is only called on one 
        client and message handlers cannot be pickled, subscribing at this time 
        would create hard-to-find synchronization bugs.
        """
        try:
            super()._check_if_forum_observation_enabled()
        except AssertionError:
            raise TokenCantSubscribeNow(self)


class TokenExtension(ForumObserver):

    def __init__(self, actor, token):
        super().__init__()
        self.actor = actor
        self.token = token

        # Iterate through all of the extension methods to find ones wanting to 
        # "watch" the token, then configure the token to call these methods 
        # whenever a token method of the same name is called.
        
        from inspect import getmembers, ismethod

        for method_name, method in getmembers(self, ismethod):

            # Methods with the '_kxg_watch_token' attribute set should be set 
            # up to watch the token.  This attribute is typically set using the
            # @watch_token decorator.

            if hasattr(method, '_kxg_watch_token'):
                token.watch_method(method_name, method)

    def __rshift__(self, message):
        return self.send_message(message)

    def send_message(self, message):
        return self.actor.send_message(message)


class TokenSerializer:

    def __init__(self, world):
        self.world = world

    def pack(self, message):
        from pickle import Pickler
        from io import BytesIO

        buffer = BytesIO()
        delegate = Pickler(buffer)

        def persistent_id(token):
            if isinstance(token, Token):
                if token.world_registration == 'pending':
                    return None
                if token.world_registration == 'active':
                    require_active_token(token)
                    return token.id
                if token.world_registration == 'expired':
                    raise UsingRemovedToken(token)

        delegate.persistent_id = persistent_id
        delegate.dump(message)

        return buffer.getvalue()

    def unpack(self, packet):
        from pickle import Unpickler
        from io import BytesIO

        buffer = BytesIO(packet)
        delegate = Unpickler(buffer)

        delegate.persistent_load = lambda id: self.world.get_token(int(id))
        return delegate.load()



