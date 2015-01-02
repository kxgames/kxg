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
