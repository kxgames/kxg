#!/usr/bin/env python3

from .errors import *
from .forums import ForumObserver
from .actors import require_actor

def read_only(method):
    setattr(method, '_kxg_read_only', True)
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
    """
    Raise an ApiUsageError if the given object is not a fully constructed 
    instance of a Token subclass.
    """
    require_instance(Token(), object)

@debug_only
def require_active_token(object):
    """
    Raise an ApiUsageError if the given object is not a token that is currently 
    participating in the game.  To be participating in the game, the given 
    token must have an id number and be associated with the world.
    """
    require_token(object)
    require_id_and_world(object)

@debug_only
def require_id_and_world(token):
    """
    Make sure the given token has an id and a reference to the world, but don't 
    confirm that it is actually a token.  The require_active_token() utility 
    makes both of these checks and is more appropriate for general use, but 
    this function is useful if you know the object in question is a properly 
    initialized token (e.g. if you already called require_token() on it).
    """
    if not token.has_id:
        raise ApiUsageError("""\
                token {token} should have an id, but doesn't.

                This error usually means that a token was added to the world 
                without being assigned an id number.  To correct this, make 
                sure that you're using a message (i.e. CreateToken) to create 
                all of your tokens.""")

    if not token.has_world:
        raise ApiUsageError("""\
                token {token} (id={token.id}) not in world.

                You can get this error if you try to remove the same token from 
                the world twice.  This might happen is you don't get rid of 
                every reference to a token after it's removed the first time, 
                then later on you try to remove the stale reference.""")


class TokenSafetyChecks(type):

    def __new__(meta, name, bases, members):
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
            meta.add_safety_checks(members)

        return super().__new__(meta, name, bases, members)
        

    @classmethod
    def add_safety_checks(meta, members):
        """
        Iterate through each member of the class being created and add a 
        safety check to every method that isn't marked as read-only.
        """
        for member_name, member_value in members.items():
            members[member_name] = meta.add_safety_check(
                    member_name, member_value)

    @staticmethod
    def add_safety_check(member_name, member_value):
        """
        If the given member is a method that is public (i.e. doesn't start with 
        an underscore) and hasn't been marked as read-only, replace it with a 
        version that will check to make sure the world is locked.  This ensures 
        that methods that alter the token are only called from update methods 
        or messages.
        """
        import functools
        from types import FunctionType

        # Bail if the given member is read-only, private, or not a method.

        is_method = isinstance(member_value, FunctionType)
        is_read_only = hasattr(member_value, '_kxg_read_only')
        is_private = member_name.startswith('_')

        if not is_method or is_read_only or is_private:
            return member_value

        def safety_checked_method(self, *args, **kwargs):
            """
            Make sure that the token the world is locked before a non-read-only 
            method is called.
            """
            # Because these checks are pretty magical, I want to be really 
            # careful to avoid raising any exceptions other than the check 
            # itself (which comes with a very clear error message).  Here, that 
            # means using getattr() to make sure the world attribute actually 
            # exists.  For example, there's nothing wrong with the following 
            # code, but it does call a safety-checked method before the world 
            # attribute is defined:
            #
            # class MyToken(kxg.Token):
            #     def __init__(self):
            #         self.init_helper()
            #         super().__init__()

            world = getattr(self, 'world', None)
            if world and world.is_locked():
                nonlocal member_name
                raise ApiUsageError("""\
                        attempted unsafe invocation of 
                        {self.__class__.__name__}.{member_name}().

                        This error brings attention to situations that might 
                        cause synchronization issues in multiplayer games.  The 
                        {member_name}() method is not marked as read-only, but 
                        it was invoked from outside the context of a message.  
                        This means that if {member_name}() makes any changes to 
                        the world, those changes will not be propagated.  If 
                        {member_name}() is actually read-only, label it with 
                        the @kxg.read_only decorator.""")

            # After making that check, call the method as usual.

            return member_value(self, *args, **kwargs)

        # Preserve any "forum observer" decorations that have been placed on 
        # the method and restore the method's original name and module strings, 
        # to make inspection and debugging a little easier.

        functools.update_wrapper(
                safety_checked_method, member_value,
                assigned=functools.WRAPPER_ASSIGNMENTS + (
                    '_kxg_subscribe_to_message',
                    '_kxg_subscribe_to_sync_response',
                    '_kxg_subscribe_to_undo_response',
                )
        )
        return safety_checked_method

        

class Token(ForumObserver, metaclass=TokenSafetyChecks):

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
        self._extensions = {}
        self._disable_forum_observation()

    def __repr__(self):
        return '{}(id={})'.format(self.__class__.__name__, self._id)

    def __getstate__(self):
        state = super().__getstate__()
        del state['_world']
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
    def has_id(self):
        return self.id is not None

    @property
    def has_world(self):
        assert (not self.world) or (self in self.world), msg("""\
                If a token has a reference to the world, it should be in the 
                world.""")
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
            raise ApiUsageError("""\
                    {self.__class__.__name__} has no such method 
                    {method_name}() to watch.

                    This error usually means that you used the @watch_token 
                    decorator on a method of a token extension class that 
                    didn't match the name of any method in the corresponding 
                    token class.  Check for typos.""")

        # Wrap the method in a WatchedMethod object, if that hasn't already 
        # been done.  This object manages a list of callback method and takes 
        # responsibility for calling them after the method itself has been 
        # called.

        if not isinstance(method, Token.WatchedMethod):
            setattr(self, method_name, Token.WatchedMethod(method))
            method = getattr(self, method_name)

        # Add the given callback to the watched method.

        method.add_watcher(callback)

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
        require_token(self)

        from .forums import IdFactory
        assert isinstance(id_factory, IdFactory), msg("""\
                The argument to Token._give_id() should be an IdFactory.  This 
                method should also only be caled by the game engine itself.""")

        if self.has_id:
            raise ApiUsageError("""\
                can't give {self} an id because it already has one.

                This error usually means that you tried to add the same token 
                to the world twice.  The first part of that process is 
                assigning an id to the token, and that doesn't make sense if 
                the token already has an id.""")

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
        except ApiUsageError:
            raise ApiUsageError("""\
                    Token {self} can't subscribe to messages now.

                    Tokens must be added to the world before they can subscribe 
                    to (or unsubscribe from) messages, because subscriptions 
                    can't be pickled and sent over the network.  So any 
                    subscriptions a token makes while it's not part of the 
                    world won't be communicated to each machine playing the 
                    game.  You are most likely getting this error because you 
                    tried to subscribe to messages in the constructor of a 
                    Token subclass.  You can't do that, but instead you can 
                    either make your subscriptions in the on_add_to_world() 
                    callback or you can label your handler methods with the 
                    @subscribe_to_message decorator.""")

    def _add_to_world(self, world, actors):
        self._world = world
        self._enable_forum_observation()
        self._create_extensions(actors)
        self.on_add_to_world(world)

    def _create_extensions(self, actors):
        self._extensions = {}
        extension_classes = self.__extend__()

        for actor in actors:
            actor_class = type(actor)
            extension_class = extension_classes.get(actor_class)

            if extension_class:

                # Raise an easy-to-understand error if the extension class's 
                # constructor takes something other than (self, actor, token).  
                # An error would be raised anyway as soon as we try to 
                # instantiate the extension, but that error would be hard to 
                # understand because it wouldn't contain the name of the 
                # offending extension and would come from pretty deep in the 
                # game engine.

                from inspect import getfullargspec
                argspec = getfullargspec(extension_class.__init__)
                if len(argspec.args) != 3:
                    raise ApiUsageError("""\
                            the {extension_class.__name__} constructor doesn't 
                            take the right arguments.

                            Token extension constructors must take exactly 
                            three arguments: self, actor, and token.  These are 
                            the arguments provided by tokens when they 
                            automatically instantiate their extensions.  Fix 
                            this error by making the {extension_class} 
                            constructor compatible with these arguments.""")

                # Instantiate the extension and store a reference to it.

                extension = extension_class(actor, self)
                self._extensions[actor] = extension

    def _remove_from_world(self):
        """
        Clear all the internal data the token needed while it was part of 
        the world.

        Note that this method doesn't actually remove the token from the 
        world.  That's what World._remove_token() does.  This method is just 
        responsible for setting the internal state of the token being removed.
        """
        self.on_remove_from_world()
        self._extensions = {}
        self._disable_forum_observation()
        self._world = None
        self._id = None


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



