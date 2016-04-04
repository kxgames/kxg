#!/usr/bin/env python3

from .errors import *
from .forums import ForumObserver
from .actors import require_actor

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
    """
    Raise an ApiUsageError if the given object is not a fully constructed 
    instance of a Token subclass.
    """
    return require_instance(Token(), object)

@debug_only
def require_active_token(object):
    """
    Raise an ApiUsageError if the given object is not a token that is currently 
    participating in the game.  To be participating in the game the given token 
    must have been added to, but not yet removed from, the world.
    """
    token = require_token(object)

    if token.world_participation == 'pending':
        if not token.has_id():
            raise TokenDoesntHaveId(token)
        if not token.has_world():
            raise TokenNotInWorld(token)
    if token.world_participation == 'removed':
        raise UsingRemovedToken(token)

    return token


class Token(ForumObserver):
    """
    Brief description...

    Tokens do not take direct responsibility for making sure they're being used 
    safely, but they do keep some information about their current participation 
    in the world, which other parts of the engine (especially the messaging 
    system) may check for sanity and safety.
    """

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
        return '{}(id={})'.format(self.__class__.__name__, self._id)

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
    def id(self):
        return self._id

    @property
    def world(self):
        return self._world

    @property
    def world_participation(self):
        """
        Return the status of this token's participation in the world.

        There are three possible world participation statuses.  The first is 
        'pending', which means that the token has not yet been added to the 
        world (although it may have been assigned an id).  The second is 
        'active', which means that the token is fully participating in the 
        world.  The third is 'removed', which means that the token has been 
        removed from the world and should no longer be in use.  These statuses 
        are mostly used for internal checks within the game engine.
        """
        if self._removed_from_world:
            return 'removed'
        elif self.has_world():
            return 'active'
        else:
            return 'pending'

    def has_id(self):
        return self.id is not None

    def has_world(self):
        assert (not self.world) or (self in self.world)
        return self.world is not None

    def has_extension(self, actor):
        require_actor(actor)
        return actor in self._extensions

    def get_extension(self, actor):
        require_actor(actor)
        return self._extensions[actor]

    def get_extensions(self):
        return list(self._extensions.values())

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

    def reset_participation(self):
        """
        Allow the token to be added to the world again.

        Once a token has been removed from the world, almost any interaction it 
        makes with the game engine (the messaging system in particular) will 
        raise an exception.  This behavior is meant to prevent bugs that happen 
        when you accidentally keep stale references to removed tokens.  Calling 
        this method turns off those checks and allows you to add a removed 
        token back into the world.  Note that this method does not actually add 
        the token to the world, it just allows you to do that in the usual way 
        (i.e. by sending a message).  This method also removes any extensions 
        associated with this token, because a new set will be created once this 
        token is added back to the world.
        """
        if self.world_participation != 'removed':
            raise CantResetActiveToken(self)
        Token.__init__(self)

    def on_add_to_world(self, world):
        pass

    def on_update_game(self, dt):
        pass

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
                if token.world_participation == 'pending':
                    return None
                if token.world_participation == 'active':
                    require_active_token(token)
                    return token.id
                if token.world_participation == 'removed':
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



