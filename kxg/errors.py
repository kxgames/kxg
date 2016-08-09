#!/usr/bin/env python3
# pylint: disable=unused-import

from nonstdlib import MagicFormatter, fmt
from nonstdlib import log, debug, info, warning, error, critical
from pprint import pprint

## Anatomy of an error message
# ============================
# 1. One line that succinctly states what the problem is.  Be mindful that 
#    errors can be raised in situations you might not have thought of, so try 
#    to phrase this line in a way that doesn't make assumptions and that won't 
#    mislead the user if it's triggered in an unexpected way.
#
# 2. In a separate paragraph, a few sentences that elaborate on the problem.  
#    In particular, try to cover the following points:
#
#   - Explain the most likely cause of the problem.  This is in slight contrast 
#     to the first line, which should strive to be context-neutral.
#
#   - Explain why this is a problem, or in other words, why the engine had to 
#     raise an exception when it encountered this scenario.
#
#   - Suggest a way to solve the problem.

## Anatomy of an assertion message
# ================================
# 1. One sentence explaining why this line should never have been reached.
#
#    "SomeClass.some_method() should've refused to ..."

## ApiUsageError vs assertions
# ============================
# Use ApiUsageError for errors that the user trigger by misusing the game 
# engine's public API.
# 
# Use assertions for errors the user should not be able to trigger without 
# changing private attributes or calling private methods.
#
# For example, there are several places where the game engine could notice that 
# the same token is being added to the world twice.  It's good for all these 
# places to make the check to be sure they're being used correctly and that a 
# token can't be added to the world twice, but only the first one should raise 
# an ApiUsageError.  The rest should be assertions, and should mention what was 
# supposed to have happened.


def format_error_message(prefix, magic_fmt_level, message, *args, **kwargs):
    import re, textwrap

    if not message:
        return ''

    # Lowercase the first letter of the error message, to enforce the 
    # recommended style.  Note that this won't have any effect if the message 
    # starts with a template argument (e.g. {}), which is actually intentional.  
    # Template arguments are often identifier names, and we don't want to 
    # change those.

    message = textwrap.dedent(message)
    message = message[0].lower() + message[1:]
    message = message | MagicFormatter(args, kwargs, magic_fmt_level)
    paragraphs = [x.strip() for x in re.split(r'\n\s*\n', message)]

    # Make sure the summary doesn't overflow its allocated space even after 
    # python adds the 'kxg.errors.ApiUsageError: ' prefix.

    summary = textwrap.fill(
            paragraphs.pop(0).replace('\n', ''),
            width=ApiUsageError.message_width,
            initial_indent=' ' * len(prefix),
    ).strip()

    # If a details paragraph was given, wrap it to fit within the allocated 
    # space.  Take care to preserve the indentation of each paragraph, 
    # which may be organizing lists and things like that.

    details = ''

    for paragraph in paragraphs:
        lines = paragraph.split('\n')
        indent_pattern = re.compile('\s*')
        initial_indent = indent_pattern.match(lines[0]).group()
        subsequent_indent = indent_pattern.match(lines[-1]).group()

        details += '\n\n' + textwrap.fill(
                paragraph.replace('\n', ''),
                width=ApiUsageError.message_width,
                initial_indent=initial_indent,
                subsequent_indent=subsequent_indent,
        )

    return summary + details

def format_assertion_message(message):
    return format_error_message('AssertionError: ', 3, message)

msg = format_assertion_message


class ApiUsageError(Exception):
    """
    Tell the user when they're misusing the game engine and suggest how they 
    should be using it instead.
    """

    message_width = 79

    def __init__(self, message, *args, **kwargs):
        prefix = '{cls.__module__}.{cls.__name__}: '.format(cls=self.__class__)
        message = format_error_message(prefix, 3, message, *args, **kwargs)
        super().__init__(message)



def debug_only(function):
    if __debug__:
        return function
    else:
        return lambda *args, **kwargs: None

@debug_only
def require_instance(prototype, object):
    prototype_cls = prototype.__class__.__name__
    object_cls = object.__class__.__name__

    if not isinstance(object, type(prototype)):
        raise ApiUsageError("""\
                expected {prototype_cls}, but got {object_cls} instead.""")

    for member_name in prototype.__dict__:
        if not hasattr(object, member_name):
            raise ApiUsageError("""\
                forgot to call the {prototype_cls} constructor in 
                {object_cls}.__init__().

                The game engine was passed an object that inherits from 
                {prototype_cls} but is missing the '{member_name}' attribute.  
                This usually means that you forgot to call the {prototype_cls} 
                constructor in your subclass.""")

