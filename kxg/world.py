#!/usr/bin/env python3

import contextlib

from .errors import *
from .tokens import Token, read_only, require_token, require_active_token

class World(Token):

    def __init__(self):
        super().__init__()
        self._id = 0
        self._tokens = {}
        self._actors = []
        self._is_locked = True
        self._has_game_ended = False
        with self._unlock_temporarily():
            self._add_token(self)

    def __repr__(self):
        return '{}()'.format(self.__class__.__name__)

    def __iter__(self):
        # Make a copy of self._tokens.values() because it's possible for tokens 
        # to be added or removed from the world while the world is being 
        # iterated through.  Concretely, this can happen when a token extension 
        # sends a message to add or remove a token during on_update_game().
        return (x for x in list(self._tokens.values()) if x is not self)

    def __len__(self):
        return len(self._tokens)

    def __contains__(self, token_or_id):
        id = token_or_id.id if isinstance(token_or_id, Token) else token_or_id
        return id in self._tokens

    def __getstate__(self):
        raise ApiUsageError("""\
can't pickle the world.

The world should never have to be pickled and sent over the network, because 
each machine starts with its own world and is kept in sync by the messaging 
system.  But unless you are explicitly trying to pickle the world on your own, 
this error is more likely to be the symptom of a major bug in the messaging 
system that is preventing it from correctly deciding which tokens need to be 
pickled.""")

    def __setstate__(self, state):
        raise AssertionError("""\
                World.__getstate__ should've refused to pickle the world.""")

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

    @read_only
    def is_locked(self):
        """
        Return whether or not the world is currently allowed to be modified.
        """
        return self._is_locked

    def end_game(self):
        self._has_game_ended = True

    @read_only
    def has_game_ended(self):
        """
        Return true if the game has ended.
        """
        return self._has_game_ended

    def on_start_game(self):
        pass

    def on_update_game(self, dt):
        for token in self:
            token.on_update_game(dt)

    def on_finish_game(self):
        pass

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
        marked as being read-only can't be called.  When the world is unlocked, 
        any token method can be called.  These checks can be disabled by 
        running python with optimization enabled.

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

    def _add_token(self, token):
        require_token(token)
        assert token.has_id, msg("""\
                token {token} should've been assigned an id by 
                Message._assign_token_ids() before World._add_token() was 
                called.""")
        assert token not in self, msg("""\
                Message._assign_token_ids() should've refused to process a 
                token that was already in the world.""")

        info('adding token to world: {token}')

        # Add the token to the world.

        self._tokens[token.id] = token
        token._add_to_world(self, self._actors)

        return token

    def _remove_token(self, token):
        require_active_token(token)
        info('removing token from world: {token}')

        id = token.id
        token._remove_from_world()
        del self._tokens[id]

    def _get_nested_observers(self):
        return iter(self)

    def _set_actors(self, actors):
        """
        Tell the world which actors are running on this machine.  This 
        information is used to create extensions for new tokens.  
        """
        self._actors = actors



@debug_only
def require_world(object):
    return require_instance(World(), object)

