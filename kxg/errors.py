#!/usr/bin/env python3
# pylint: disable=unused-import

from nonstdlib import log, debug, info, warning, error, critical

class ApiUsageError(Exception):
    """
    A class for communicating errors to the user.
    """

    message_width = 79

    def __init__(self, message):
        import re, textwrap

        width = ApiUsageError.message_width
        message = textwrap.dedent(message)
        tokens = [x.strip() for x in re.split(r'\n\s*\n', message, 1)]

        # Make sure the summary doesn't overflow 80 characters even after 
        # python adds the 'kxg.errors.ApiUsageError: ' prefix.

        prefix = (
                self.__class__.__module__ + '.' +
                self.__class__.__name__ + ': '
        )
        summary = textwrap.fill(
                tokens.pop(0), width=width, initial_indent=' ' * len(prefix),
        ).strip()

        # If a details paragraph was given, wrap it to fit in 80 characters.

        if tokens:
            details = tokens.pop(0).replace('\n', '')
            details = '\n\n' + textwrap.fill(details, width=width)
        else:
            details = ''

        super().__init__(summary + details)


class ApiUsageErrorFactory:
    """
    Factory class for making nicely formatted exceptions.

    ApiUsageError is the only kind of exception raised by the game engine.  
    Different kinds of errors are distinguished by different error messages, 
    but not by different classes.  The reason for this is mostly aesthetic: 
    every message prints out a brief sentence describing the problem, and this 
    sentence makes a specific class name redundant.  Specific error class names 
    can also be quite long.  

    However, the engine still needs an easy way to raise API usage errors with 
    different error messages.  The solution to this problem is this class: 
    ApiUsageErrorFactory.  This class is meant to be subclassed.  Each subclass 
    represents a single type of error and knows both how to describe that error 
    and when to raise that error.

    To define a new type of error, start by making a new ApiUsageErrorFactory 
    subclass.  You can overload the get_message() method to return a message 
    describing your error.  You can also use the default implementation, which 
    is basically just 'return self.message.format(**self.__dict__)'.  In other 
    words, you can just provide an attribute called 'message' attribute which 
    may contain formatting references to any other attribute of your class 
    (e.g. "Token {token} has a bad id." if your class has a 'token' attribute.)  
    This default approach should work well for most cases.

    You error message should be composed of a one-line summary and a multi-line 
    description.  The summary and the description should be separated by a 
    blank line.  This format is parsed by ApiUsageError so it can format the 
    message nicely.  The summary should simple state what went wrong.  The 
    description should elaborate on that and should suggest the most likely 
    causes and solutions.

    You can also implement the error_condition() method to return whether or 
    not the error in question should be raised.  This method is used by the 
    raise_if_warranted() method to decide whether or not the exception should 
    be raised.  I also think it's good practice to keep description of the 
    error and the logic for raising the error in the same place.

    Note that when you try to construct an instance of an ApiUsageErrorFactory 
    subclass, you are actually returned an ApiUsageError instance.  So:

    >>> class SirRobinRanAway(ApiUsageErrorFactory): pass
    >>> type(SirRobinRanAway())
    <class 'kxg.ApiUsageError'>

    This is accomplished using some python magic involving __new__() and is 
    meant to cut down on boilerplate.  But I can also see it being confusing 
    if you're looking at things closely.  The best way to think about this is 
    to remember that your factory classes are really factories, and that the 
    constructor is the when the exception is created.
    """

    message = "Unknown error."

    def __new__(cls, *args, **kwargs):
        factory = object.__new__(cls)
        factory.__init__(*args, **kwargs)
        message = factory.message.format(**factory.__dict__)

        # Normally, we want to lowercase the first letter in every error 
        # message to force adherence to the recommended python style.  The 
        # exception is if the first character in the unformatted message is a 
        # brace, which means that the message probably begins with some 
        # identifier name.  In that case we don't want to change anything.

        if not factory.message.startswith('{'):
            message = message[0].lower() + message[1:]

        return ApiUsageError(message)



class CantModifyTokenIfWorldLocked(ApiUsageErrorFactory):

    message = """\
attempted unsafe invocation of {token_class}.{method_name}().

This error brings attention to situations that might cause synchronization 
issues in multiplayer games.  The {method_name}() method is not marked as 
read-only, but it was invoked from outside the context of a message.  This 
means that if {method_name}() makes any changes to the world, those changes 
will not be propagated.  If {method_name}() is actually read-only, label it 
with the @kxg.read_only decorator."""

    def __init__(self, token, method_name):
        self.token = token
        self.token_class = token.__class__.__name__
        self.method_name = method_name


class CantModifyTokenIfNotInWorld(ApiUsageErrorFactory):

    message = """\
may have forgotten to add {token} to the world.

The {token_class}.{method_name}() method was invoked on a token that had not 
yet been added to the game world.  This is usually a sign that you forgot to 
add the token in question was to the game world.  Label the {method_name}() 
method with the @kxg.before_world decorator if you really do need to call it 
before the token has been added to the world (i.e. the method helps setup 
{token_class} tokens)."""

    def __init__(self, token, method_name):
        self.token = token
        self.token_class = token.__class__.__name__
        self.method_name = method_name


class CantPickleWorld(ApiUsageErrorFactory):

    message = """\
can't pickle the world.

The world should never have to be pickled and sent over the network, because 
each machine starts with its own world and is kept in sync by the messaging 
system.  But unless you are explicitly trying to pickle the world on your own, 
this error is more likely to be the symptom of a major bug in the messaging 
system that is preventing it from correctly deciding which tokens need to be 
pickled."""

class CantResetActiveToken(ApiUsageErrorFactory):

    message = """\
token {token} can't be reset because it's still being used.

The purpose of Token.reset_registration() is to allow you to reuse tokens that 
were previously removed from the world.  Normally these tokens aren't allowed 
to do anything, which makes it easy to know when you accidentally keep a stale 
reference to a token that isn't part of the world anymore.  This error means 
that you tried to reset a token that was never removed from the world (or that 
was already reset)."""

    def __init__(self, token):
        self.token = token


class CantReuseMessage(ApiUsageErrorFactory):

    message = """\
can't send the same message more than once.

It's not safe to send the same message twice because messages can accumulate 
state as they are executed.  This also breaks the system by which clients can 
react to responses from the server in multiplayer games.
"""
class IllegalTokenExtensionConstructor(ApiUsageErrorFactory):

    message = """\
the {extension_cls} constructor doesn't take the right arguments.

Token extension constructors must take exactly three arguments: self, actor, 
and token.  These are the arguments provided by tokens when they automatically 
instantiates their extensions.  Fix this error by making the {extension_cls} 
constructor compatible with these arguments."""

    def __init__(self, extension_cls):
        self.extension_cls = extension_cls.__name__


class MessageNotYetSent(ApiUsageErrorFactory):

    message = """\
can't ask who sent a message before it's been sent.

This error means Message.was_sent_by() or Message.was_sent_by_referee() got 
called on a message that hadn't been sent yet.  Normally you would only call 
these methods from within Message.on_check()."""

class MessageAlreadySent(ApiUsageErrorFactory):

    message = """\
messages can't add or remove tokens after they've been sent.

You get this error if you call Message.add_token() or Message.remove_token() 
after the message has been sent.  Normally you would only call these methods 
from within the constructors of your message subclasses."""

class NotUsingIdFactory(ApiUsageErrorFactory):

    message = """\
can't use {bad_id} as a token id.

Token._give_id() expects to be passed an internal object that can be used to 
create new, unique id numbers.  For that reason, this method should only be 
called by the game engine.  You can get this error if you try to assign an id 
to a token by calling Token._give_id() yourself.  Use Message.add_token() to 
create all your tokens in a manner that avoids synchronization bugs."""

    def __init__(self, bad_id):
        self.bad_id = bad_id


class ObjectIsntRightType(ApiUsageErrorFactory):

    message = """\
expected {prototype_cls}, but got {object_cls} instead."""

    def __init__(self, prototype, object):
        self.prototype = prototype
        self.prototype_cls = prototype.__class__.__name__
        self.object = object
        self.object_cls = object.__class__.__name__


class ObjectIsntFullyConstructed(ApiUsageErrorFactory):

    message = """\
forgot to call the {prototype_cls} constructor in {object_cls}.__init__().

The game engine was passed an object that inherits from {prototype_cls} but is 
missing the '{missing_member}' attribute.  This usually means that you forgot 
to call the {prototype_cls} constructor in your subclass."""

    def __init__(self, prototype, object, missing_member):
        self.prototype = prototype
        self.prototype_cls = prototype.__class__.__name__
        self.object = object
        self.object_cls = object.__class__.__name__
        self.missing_member = missing_member


class ObjectIsntMessageSubclass(ApiUsageErrorFactory):

    message = """\
expected Message subclass, but got {object} instead."""

    def __init__(self, object):
        try:
            self.object = object.__name__
        except:
            self.object = object


class TokenAlreadyHasId(ApiUsageErrorFactory):

    message = """\
token {token} already has an id.

This error usually means that {token} was added to the world twice."""

    def __init__(self, token):
        self.token = token


class TokenAlreadyInWorld(ApiUsageErrorFactory):

    message = """\
can't add the same token to the world twice.

Token {token} can't be added to the world, because the world already contains a 
token with the id={token.id}.  You can get this error if you try to add a token 
to the world on without using a message (i.e. CreateToken)."""

    def __init__(self, token):
        self.token = token


class TokenDoesntHaveId(ApiUsageErrorFactory):

    message = """\
token {token} should have an id, but doesn't.

This error usually means that a token was added to the world without being 
assigned an id number.  To correct this, make sure that you're using a message 
(i.e. CreateToken) to create all of your tokens."""

    def __init__(self, token):
        self.token = token


class TokenCantSubscribeNow(ApiUsageErrorFactory):

    message = """\
token {token} can't subscribe to messages now.

Tokens must be registered with the world before they can subscribe to (or 
unsubscribe from) messages, because subscriptions can't be pickled and sent 
over the network.  So any subscriptions a token makes while it's not part of 
the world won't be communicated to each machine playing the game.  You are most 
likely getting this error because you tried to subscribe to messages in the 
constructor of a Token subclass.  You can't do that, but instead you can either 
make your subscriptions in the on_add_to_world() callback or you can label your 
handler methods with the @subscribe_to_message decorator."""

    def __init__(self, token):
        self.token = token


class TokenCantUseStaleReporter(ApiUsageErrorFactory):
    
    message = """\
tokens can't send messages outside of report().

The engine detected a '{message.__class__.__name__}' message being sent to a 
reporter that is no longer accepting messages.  This can happen if you save the 
reporter object passed to Token.report() and attempt to use it outside of that 
method call."""

class TokenHasNoSuchMethodToWatch(ApiUsageErrorFactory):

    message = """\
{token_cls} has no such method {method_name}() to watch.

This error usually means that you used the @watch_token decorator on a method 
of a token extension class that didn't match the name of any method in the 
corresponding token class.  Check for typos."""

    def __init__(self, token, method_name):
        self.token = token
        self.token_cls = token.__class__.__name__
        self.method_name = method_name


class TokenNotInWorld(ApiUsageErrorFactory):

    message = """\
token {token} (id={token.id}) not in world.

You can get this error if you try to remove the same token from the world 
twice.  This might happen is you don't get rid of every reference to a token 
after it's removed the first time, then later on you try to remove the stale 
reference."""

    def __init__(self, token):
        self.token = token


class UsingRemovedToken(ApiUsageErrorFactory):

    message = """\
token {token} has been removed from the world.

This error is raised when the game engine detects that a token that has been 
removed from world is still being used.  For example, maybe a message can't be 
pickled because it contains a reference to a token that was previously removed 
from the world.  This error usually means that a stale reference to a destroyed 
token is accidentally being kept."""

    def __init__(self, token):
        self.token = token


class UsingStaleReporter(ApiUsageErrorFactory):

    message = """\
{message_cls} message sent using a stale reporter.

This message is raised when the reporter provided to Token.report() is used 
after that method returns.  This can only happen if you save a reference to the 
reporter, which you shouldn't do.  This is a multiplayer synchronization issue.  
Because the same token should exist in the same state on every machine playing 
the game, tokens normally can't send messages or they would be prone to sending 
duplicate messages.  The exception is Token.report(), which is guaranteed to be 
called only on the server.  Token.report() is provided with a reporter object 
that can be used to send messages, but it's illegal to save a reference to the 
reporter and use it after Token.report() returns.  Such a design would lead to 
bugs on the clients, which are never given reporter objects."""

    def __init__(self, message):
        self.message_cls = message.__class__.__name__


class UnhandledSyncError(ApiUsageErrorFactory):

    message = """\
the message {message_} was rejected by the server.

This client attempted to send a {message_cls} message, but it was rejected by 
the server.  To fix this error, either figure out why the client is getting out 
of sync with the server or implement a {message_cls}.on_undo() that undoes 
everything done in {message_cls}.on_execute()."""

    def __init__(self, message):
        self.message_ = message
        self.message_cls = message.__class__.__name__


class WorldAlreadyUnlocked(ApiUsageErrorFactory):

    message = """\
tired to unlock the world, but it's already unlocked.

You can't get this error unless you manually call World._unlock_temporarily(), 
which you should never do.  This method is intended to be used by the game 
engine, which was carefully designed to allow the world to be modified only 
when safe.  Calling this method yourself disables an important safety check.
"""

def debug_only(function):
    if __debug__:
        return function
    else:
        return lambda *args, **kwargs: None

@debug_only
def require_instance(prototype, object):
    if not isinstance(object, type(prototype)):
        raise ObjectIsntRightType(prototype, object)

    for member_name in prototype.__dict__:
        if not hasattr(object, member_name):
            raise ObjectIsntFullyConstructed(prototype, object, member_name)

    return object

