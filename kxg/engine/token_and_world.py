import functools
import contextlib
from .forum_observer import ForumObserver
from .errors import *
from pprint import pprint

class TokenMetaclass (type):

    read_only_flag = '__read_only__'
    before_setup_flag = '__before_setup__'
    after_teardown_flag = '__after_teardown__'

    read_only_special_cases = '__str__', '__repr__'
    before_setup_special_cases = '__init__', '__extend__'

    class TokenSetupError (GameEngineError):

        message = "May have forgotten to add {0} to the world."
        details = """\
                The {0}.{1}() method was invoked on a token that had not yet 
                been added to the game world.  This is usually a sign that the 
                token in question was never added to the game world.  Label the 
                {1}() method with the kxg.before_setup decorator if you do 
                need it to setup {0} tokens."""

        def __init__(self, token, method):
            class_name = token.__class__.__name__
            method_name = method.__name__

            self.method = method
            self.format_arguments(class_name, method_name)

        def raise_if_warranted(self):
            if not hasattr(self.method, TokenMetaclass.before_setup_flag):
                raise self

    class TokenAccessError (GameEngineError):

        message = "Attempted unsafe invocation of {0}.{1}()."
        details = """\
                This error is meant to bring attention to situations that might 
                cause synchronization issues in multiplayer games.  The {1}() 
                method is not marked as read-only, but it was invoked from 
                outside the context of a message.  This means that if {1}() 
                makes any changes to the world, those changes will not be 
                propagated. If {1}() is actually read-only, mark it with the 
                @kxg.read_only decorator."""

        def __init__(self, token, method):
            class_name = token.__class__.__name__
            method_name = method.__name__

            self.method = method
            self.format_arguments(class_name, method_name)

        def raise_if_warranted(self):
            if Token._locked:
                raise self

    class TokenTeardownError (GameEngineError):

        message = "May not have completely removed {0} from the world."
        details = """\
                The {0}.{1}() method was invoked on a token that has already 
                been removed from the game world.  This is usually a sign that 
                not all references to this token were purged when it was 
                removed.  If you simply need to invoke the {1}() method after 
                teardown, label it with the kxg.after_teardown decorator."""

        def __init__(self, token, method):
            class_name = token.__class__.__name__
            method_name = method.__name__

            self.method = method
            self.format_arguments(class_name, method_name)

        def raise_if_warranted(self):
            if not hasattr(self.method, TokenMetaclass.after_teardown_flag):
                raise self


    def __new__(meta, name, bases, members):
        from types import FunctionType

        for member_name, member_value in members.items():
            is_function = (type(member_value) == FunctionType)
            is_before_setup = member_name in meta.before_setup_special_cases
            is_read_only = hasattr(member_value, meta.read_only_flag) or \
                    member_name in meta.read_only_special_cases

            if is_function and is_before_setup:
                member_value = TokenMetaclass.before_setup(member_value)
            if is_function and not is_read_only:
                member_value = TokenMetaclass.check_for_safety(member_value)

            members[member_name] = member_value

        return type.__new__(meta, name, bases, members)

    @classmethod
    def check_for_safety(meta, method):
        """ Decorate the given method so that it will complain if invoked in a 
        dangerous way.  This mostly means checking to make sure that methods 
        which alter the token are only called from messages. """

        # Access control checks help find bugs, but they may also incur 
        # significant computational expense.  By invoking python with 
        # optimization enabled (i.e. passing -O) these checks are disabled.  

        if not __debug__:
            return method

        @functools.wraps(method)
        def decorator(self, *args, **kwargs):
            if self.is_before_setup():
                meta.TokenSetupError(self, method).raise_if_warranted()

            elif self.is_registered():
                NullTokenIdError(self).raise_if_warranted()
                meta.TokenAccessError(self, method).raise_if_warranted()

            elif self.is_after_teardown():
                meta.TokenTeardownError(self, method).raise_if_warranted()

            else:
                UnknownTokenStatus(self).raise_unconditionally()

            return method(self, *args, **kwargs)

        return decorator

    @classmethod
    def read_only(meta, method):
        setattr(method, meta.read_only_flag, True)
        return method

    @classmethod
    def before_setup(meta, method):
        setattr(method, meta.before_setup_flag, True)
        return method

    @classmethod
    def after_teardown(meta, method):
        setattr(method, meta.after_teardown_flag, True)
        return method



def read_only(method):
    return TokenMetaclass.read_only(method)

def before_setup(method):
    return TokenMetaclass.before_setup(method)

def after_teardown(method):
    return TokenMetaclass.after_teardown(method)

def check_for_prototype(method):
    @functools.wraps(method)
    def decorator(self, *args, **kwargs):
        self.check_for_prototype()
        return method(self, *args, **kwargs)
    return decorator

def check_for_instance(method):
    @functools.wraps(method)
    def decorator(self, *args, **kwargs):
        self.check_for_instance()
        return method(self, *args, **kwargs)
    return decorator


class Token (ForumObserver):
    __metaclass__ = TokenMetaclass

    _locked = True
    _before_setup = 'before setup'
    _registered = 'registered'
    _after_teardown = 'after teardown'

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
        # Normally I would define all the members that would be used by a class 
        # in its constructor, but in this case doing so is problematic because 
        # tokens are often pickled and sent across the network.  So anything 
        # defined here would needlessly use up a few bytes of bandwidth.  To 
        # compensate for variables not being predefined in the constructor, the 
        # rest of the class uses hasattr() check where appropriate.
        super().__init__()

    def __extend__(self):
        return {}

    @read_only
    def watch_method(self, method_name, callback):
        """
        Register the given callback to be called whenever the method with the 
        given name is called.  You can easily take advantage of this feature in 
        token extension by using the @watch_token decorator.
        """

        # Make sure a token method with the given name exists, and complain if 
        # nothing is found.

        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise TokenWatchingError(method_name)

        # Wrap the method in a WatchedMethod object, if that hasn't already 
        # been done.  This object manages a list of callback method and takes 
        # responsibility for calling them after the method itself has been 
        # called.

        if not isinstance(method, Token.WatchedMethod):
            setattr(token, method_name, Token.WatchedMethod(method))
            method = getattr(self, method_name)

        # Add the given callback to the watched method.

        method.add_watcher(callback)

    @read_only
    def get_id(self):
        return self._id

    @before_setup
    def give_id(self, id):
        assert not hasattr(self, '_id'), "Token already has an id."
        assert self.is_before_setup(), "Token already registered with the world."
        self._id = id.next()

    @read_only
    def is_before_setup(self):
        before_setup = Token._before_setup
        return getattr(self, '_status', before_setup) == before_setup

    @read_only
    def is_registered(self):
        return getattr(self, '_status', None) == Token._registered

    @read_only
    def is_after_teardown(self):
        return getattr(self, '_status', None) == Token._after_teardown

    @read_only
    def has_extension(self, actor):
        try: return type(actor) in self._extensions
        except AttributeError: return False

    @read_only
    def get_extension(self, actor):
        return self._extensions[type(actor)]

    @read_only
    def get_extensions(self):
        return self._extensions.values()

    def on_add_to_world(self, world):
        pass

    def on_update_game(self, dt):
        pass

    @read_only
    def on_report_to_referee(self, reporter):
        pass

    def on_remove_from_world(self):
        pass

    def _require_active_observer(self):
        # Give a helpful error if the user attempts to use the ForumObserver 
        # before it has been configured.  One common way this might happen is 
        # if the user attempts to subscribe to messages in the constructor.  
        # This is rightly forbidden, because there would be no way to copy 
        # those subscriptions to all the other clients.

        try: super()._require_active_observer()
        except: raise TokenMessagingDisabled()


class World (Token):

    def __init__(self):
        super().__init__()
        self._configure_observer()

        self._id = 0
        self._tokens = {self.get_id(): self}
        self._actors = []

    @read_only
    def __str__(self):
        return '<World len=%d>' % len(self)

    @read_only
    def __iter__(self):
        yield from self._tokens.values()

    @read_only
    def __len__(self):
        return len(self._tokens)

    @read_only
    def __contains__(self, token):
        return token.get_id() in self._tokens

    @before_setup
    def set_actors(self, actors):
        """
        Tell the world which actors are running on this machine.

        The world uses this information to create extensions for new tokens.  
        This method also marks the world as having been "registered", so until 
        it is called, you can only use world methods marked with @before_setup.
        """
        self._actors = actors
        self._status = Token._registered

    @read_only
    def get_token(self, id):
        return self._tokens[id]

    @read_only
    def get_last_id(self):
        return max(0, *self._tokens)

    def has_game_started(self):
        raise NotImplementedError

    def has_game_ended(self):
        raise NotImplementedError

    def on_start_game(self):
        pass

    def on_update_game(self, dt):
        for token in self:
            if token is not self:
                token.on_update_game(dt)

    def on_finish_game(self):
        pass

    def _add_token(self, token):
        id = token.get_id()
        assert id is not None, "Can't register a token with a null id."
        assert id not in self._tokens, "Can't reuse %d as an id number." % id
        assert isinstance(id, int), "Token has non-integer id number."

        self._tokens[id] = token
        token._status = Token._registered

        # Allow the token to subscribe and unsubscribe from messages delivered 
        # by the forum.
        token._configure_observer()

        token.on_add_to_world(self)

        token._extensions = {}
        extension_classes = token.__extend__()

        for actor in self._actors:
            actor_class = type(actor)
            extension_class = extension_classes.get(actor_class)

            if extension_class:
                extension = extension_class(actor, token)
                token._extensions[actor_class] = extension

        return token

    def _remove_token(self, token):
        id = token.get_id()
        assert id is not None, "Can't remove a token with a null id."
        assert isinstance(id, int), "Token has non-integer id number."
        assert token.is_registered(), "Can't remove an unregistered token."

        del self._tokens[id]
        token.on_remove_from_world()
        token._status = Token._after_teardown

    def _get_nested_observers(self):
        return filter(lambda t: t is not self, self)


class Prototype (Token):

    def __init__(self, id):
        Token.__init__(self, id)
        self._instantiated = False

    @check_for_prototype
    def instantiate(self, id):
        from copy import deepcopy
        instance = deepcopy(self)
        Token.__init__(instance, id)
        instance._instantiated = True
        return instance

    def check_for_prototype(self):
        assert not self._instantiated

    def check_for_instance(self):
        assert self._instantiated


class TokenExtension (ForumObserver):

    def __init__(self, actor, token):
        super().__init__()
        self._configure_observer()
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

            if not hasattr(method, '_kxg_watch_token'):
                break

            # Tell the token to call the extension method whenever the matching 
            # token method is called.

            token.watch_method(method_name, method)

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
                if token.is_registered():
                    return token.get_id()
                if token.is_after_teardown():
                    raise UsingDestroyedToken(token)

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

@contextlib.contextmanager
def unrestricted_token_access():
    # I feel like this should be a method of the world.  And tokens should look 
    # to the world in check_for_safety().  That would make it so you could do 
    # anything to a token before it becomes part of the world.
    Token._locked = False
    try: yield
    finally: Token._locked = True



