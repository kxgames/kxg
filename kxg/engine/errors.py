# Right now, for no good reason, there are two exception hierarchies.  At some 
# point this should be condensed back down to one.

# There should be one unit test for each type of error in this file.  For one 
# thing, I'll need that to get 100% coverage.  But it also just makes sense.

class GameEngineError (Exception):

    def __init__(self):
        self.format_args = ()
        self.format_kwargs = {}

    def __str__(self):
        import sys, textwrap

        try:
            indent = '    '
            format_args = self.format_args
            format_kwargs = self.format_kwargs

            message = self.message.format(*format_args, **format_kwargs)
            message = textwrap.dedent(message)
            message = textwrap.fill(message,
                    initial_indent=indent, subsequent_indent=indent)

            if self.details:
                details = self.details.format(*format_args, **format_kwargs)
                details = details.replace(' \n', '\n')
                details = textwrap.dedent(details)
                details = '\n\n' + textwrap.fill(details, 
                        initial_indent=indent, subsequent_indent=indent)
            else:
                details = ''

            return '\n' + message + details

        except Exception as error:
            import traceback
            return "Error in exception class: %s" % error


    def format_arguments(self, *args, **kwargs):
        self.format_args = args
        self.format_kwargs = kwargs

    def raise_if(self, condition):
        if condition: raise self

    def raise_if_not(self, condition):
        if not condition: raise self

    def raise_if_warranted(self):
        raise NotImplementedError


class NullTokenIdError (GameEngineError):

    message = "Token {0} has a null id."
    details = """\
            This error usually means that a token was added to the world 
            without being assigned an id number.  To correct this, make sure 
            that you're using a CreateToken message to create this token."""

    def __init__(self, token):
        self.token = token
        self.format_arguments(token)

    def raise_if_warranted(self):
        if self.token.get_id() is None:
            raise self


class UnexpectedTokenIdError (GameEngineError):

    message = "Token {0} already has an id."
    details = "This error usually means that {0} was added to the world twice."

    def __init__(self, token):
        self.token = token
        self.format_arguments(token)

    def raise_if_warranted(self):
        if self.token.get_id() is not None:
            raise self


class UnknownTokenStatus (GameEngineError):

    message = "Token has unknown status '{0}'."

    def __init__(self, token):
        self.status = token._status
        self.format_arguments(self.status)

    def raise_if_warranted(self):
        known_statuses = (
                Token._before_setup,
                Token._register,
                Token._after_teardown)

        if self.status not in self.known_statuses:
            raise self


class TokenMessagingDisabled (GameEngineError):

    message = """\
            Tokens must be registered with the world in order to subscribe or 
            unsubscribe from messages."""
    details = ""


class KxgError (Exception):
    pass

class MessageSenderError (KxgError):

    def __init__(self, sender, message):
        KxgError.__init__(self, """\

                """)

class ImmutableMessageError (KxgError):

    def __init__(self, message):
        KxgError.__init__(self, """\
attempting to set a message attribute at a bad time

You are only allowed to set message attributes in methods that are only called 
on one machine.  This ensures that the same message doesn't end up with 
different state on different machines.  Typically you get this error by setting 
a message in attribute in Message.execute(), but you should consult the online 
documentation for the complete list of immutable methods.""")

class StaleReporterError (KxgError):
    
    def __init__(self, message):
        KxgError.__init__(self, """\
tokens can't send messages outside of report()

The engine detected a '{}' message being sent to a reporter that is no longer 
accepting messages.  This can happen if you save the reporter object passed to 
Token.report() and attempt to use it outside of that method call.""")

class UnhandledSyncError (KxgError):
    pass

class TokenWatchingError (KxgError):
    pass

