#!/usr/bin/env python3

import contextlib

from .errors import *
from .tokens import Token, read_only, before_world
from .tokens import require_token, require_active_token

class World (Token):

    def __init__(self):
        super().__init__()
        self._id = 0
        self._tokens = {}
        self._actors = []
        self._is_locked = True
        with self._unlock_temporarily():
            self._add_token(self)

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
        return token.id in self._tokens

    def __getstate__(self):
        raise CantPickleWorld()

    def __setstate__(self, state):
        raise CantPickleWorld()

    @read_only
    def get_token(self, id):
        """
        Return the token with the given id.  If no token with the given id is 
        registered to the world, an IndexError is thrown.
        """
        return self._tokens[id]

    @read_only
    def get_last_id(self):
        """
        Return the largest token id registered with the world.  If no tokens 
        have been added to the world, the id for the world itself (0) is 
        returned.  This means that the first "real" token id is 1.
        """
        return max(self._tokens)

    def set_actors(self, actors):
        """
        Tell the world which actors are running on this machine.  This 
        information is used to create extensions for new tokens.  
        """
        self._actors = actors

    @read_only
    def is_locked(self):
        """
        Return whether or not the world is currently allowed to be modified.
        """
        return self._is_locked

    @read_only
    def has_game_started(self):     # (pure virtual)
        """
        Return true if the game has started.  This is a pure-virtual method 
        that must be implemented in subclasses.
        """
        raise NotImplementedError

    @read_only
    def has_game_ended(self):       # (pure virtual)
        """
        Return true if the game has ended.  This is a pure-virtual method 
        that must be implemented in subclasses.
        """
        raise NotImplementedError

    def on_start_game(self):
        pass

    def on_update_game(self, dt):
        for token in self:
            if token is not self:
                token.on_update_game(dt)

    def on_finish_game(self):
        pass

    @read_only
    @contextlib.contextmanager
    def _unlock_temporarily(self):
        """
        Allow tokens to modify the world for the duration of a with-block.

        It's important that tokens only modify the world at appropriate times, 
        otherwise the changes they make may not be communicated across the 
        network to other clients.  To help catch and prevent these kinds of 
        errors, the game engine keeps the world locked most of the time and 
        only briefly unlocks it (using this method) when tokens are allowed to 
        make changes.  When the world is locked, token methods that aren't 
        marked as being read-only can't be called. only allows token methods 
        When the world is unlocked, any token method can be called.  These 
        checks can be disabled by running python with optimization enabled.

        You should never call this method manually from within your own game.  
        This method is intended to be used by the game engine, which was 
        carefully designed to allow the world to be modified only when safe.  
        Calling this method yourself disables an important safety check.
        """
        if not self._is_locked:
            yield
        else:
            try:
                self._is_locked = False
                yield
            finally:
                self._is_locked = True

    @before_world
    def _add_token(self, token):
        require_token(token)
        if token.world_registration == 'pending' and not token.has_id():
            raise TokenDoesntHaveId(token)
        if token.world_registration == 'active':
            raise TokenAlreadyInWorld(token)
        if token.world_registration == 'expired':
            raise UsingRemovedToken(token)

        # Add the token to the world.  This means adding it to the world's list 
        # of tokens, giving it a reference to the world (which allows it to 
        # use methods that haven't been marked with @before_setup), and 
        # allowing it to subscribe to messages from the forum.

        id = token.id
        self._tokens[id] = token
        token._world = self
        token._removed_from_world = False
        token._enable_forum_observation()

        # Initialize any extensions relevant to this token.  Which extensions 
        # are relevant depends on which actors are being are running on the 
        # current machine.  At most one extension will be created per actor.

        token._extensions = {}
        extension_classes = token.__extend__()

        for actor in self._actors:
            actor_class = type(actor)
            extension_class = extension_classes.get(actor_class)

            if extension_class:
                extension = extension_class(actor, token)
                token._extensions[actor_class] = extension

        # Finally, give the token a chance to react to it's own creation.

        token.on_add_to_world(self)

        return token

    def _remove_token(self, token):
        require_active_token(token)

        # Remove the token from the world.  The token is given a chance to 
        # react to its destruction, then forum observation is disabled.

        token.on_remove_from_world()
        token._disable_forum_observation()
        token._extensions = {}
        token._removed_from_world = True
        token._world = None

        id = token.id
        del self._tokens[id]

        token._id = None

    def _get_nested_observers(self):
        return filter(lambda t: t is not self, self)



@debug_only
def require_world(object):
    return require_instance(World(), object)

