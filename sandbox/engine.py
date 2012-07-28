class GameEngine (object):

    def update(self):

        for actor in self.actors:
            with self.set_permissions(actor):
                actor.update()

        for message in self.messages:

            message.validate()

            with self.allow_changes():
                message.execute()

            for actor in self.actors():
                with self.set_permissions(actor):
                    message.inform(actor)

    def set_permissions(self, actor):

        Proxy._security = 'enforcing'
        Proxy._actor = actor.get_name()

        # Reset permissions on exit.

    def allow_changes(self):

        Proxy._security = 'permissive'
        Proxy._actor = None

        # Reset permissions on exit.

class ProxyLock:

    def __init__(self, access, actor=None):
        self.current_access = access
        self.current_actor = actor

    def __enter__(self):
        self.previous_access = Proxy._access
        self.previous_actor = Proxy._actor

        Proxy._access = self.current_access
        Proxy._actor = self.current_actor

    def __exit__(self, *args, **kwargs):
        Proxy._access = self.previous_access
        Proxy._actor = self.previous_actor

    @staticmethod
    def restrict_default_access():
        Proxy._access = 'protected'


class ProtectedProxyLock (ProxyLock):
    def __init__(self, actor):
        Lock.__init__(self, 'protected', actor)

class UnprotectedProxyLock (ProxyLock):
    def __init__(self):
        Lock.__init__(self, 'unprotected', None)

class GameTokenProxy (object):

    _access = 'unprotected'
    _actor = None

    def __init__(self, token):

        self._token = token
        self._extensions = {
                actor : extension_class(self)
                for actor, extension_class in token.__extend__().items() }

    def __getattr__(self, key):

        access = Proxy._access
        actor = Proxy._actor

        token = self._token
        extension = self._extensions.get(actor)

        if hasattr(token, key):
            member = getattr(token, key)

            if access == 'unprotected' or hasattr(member, 'read_only'):
                return member
            else:
                raise PermissionError(key)

        elif extension and hasattr(extension, key):
            return getattr(extension, key)

        else:
            raise AttributeError(key)

class GameToken (object):

    def __new__(cls, *args, **kwargs):

        token = object.__new__(cls, *args, **kwargs)
        token.__init__(*args, **kwargs)
        proxy = Proxy(token)

        return proxy

    def __extend__(self):
        return {}

class GameTokenExtension (object):

    def __init__(self, token):
        pass

class TokenPermissionError (Exception):
    pass

def data_getter(method):
    method.read_only = True
    return method

