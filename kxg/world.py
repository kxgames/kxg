#!/usr/bin/env python3

import contextlib

from .errors import *
from .tokens import Token, require_token, require_active_token

class World(Token):

    def __init__(self):
        super().__init__()
        self._id = 0
        self._tokens = {}
        self._actors = []
        self._has_game_ended = False
        self._add_token(self)

    def __repr__(self):
        return '{}()'.format(self.__class__.__name__)

    def __iter__(self):
        # The reason for making a copy of self._tokens.values() is that it's 
        # possible for tokens to be added or removed from the world while the 
        # world is being iterated through.  Concretely, this can happen when a 
        # token extension sends a message to add or remove a token during 
        # on_update_game().
        return (x for x in list(self._tokens.values()) if x is not self)

    def __len__(self):
        return len(self._tokens)

    def __contains__(self, token_or_id):
        id = token_or_id.id if isinstance(token_or_id, Token) else token_or_id
        return id in self._tokens

    def __getstate__(self):
        raise CantPickleWorld()

    def __setstate__(self, state):
        raise CantPickleWorld()     # pragma: no cover

    def get_token(self, id):
        """
        Return the token with the given id.  If no token with the given id is 
        registered to the world, an IndexError is thrown.
        """
        return self._tokens[id]

    def get_last_id(self):
        """
        Return the largest token id registered with the world.  If no tokens 
        have been added to the world, the id for the world itself (0) is 
        returned.  This means that the first "real" token id is 1.
        """
        return max(self._tokens)

    def end_game(self):
        self._has_game_ended = True

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

    def _add_token(self, token):
        require_token(token)
        if token.world_participation == 'pending' and not token.has_id():
            raise TokenDoesntHaveId(token)
        if token.world_participation == 'active':
            raise TokenAlreadyInWorld(token)
        if token.world_participation == 'removed':
            raise UsingRemovedToken(token)

        # Add the token to the world.  This means adding it to the world's list 
        # of tokens, giving it a reference to the world, and allowing it to 
        # subscribe to messages from the forum.

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

                # Make sure the extension class constructor takes exactly three 
                # arguments: self, actor, token.  If the constructor has a 
                # different signature, raise an error with a helpful message.

                from inspect import getfullargspec
                argspec = getfullargspec(extension_class.__init__)
                if len(argspec.args) != 3:
                    raise IllegalTokenExtensionConstructor(extension_class)

                # Instantiate the extension and store a reference to it.

                extension = extension_class(actor, token)
                token._extensions[actor] = extension

        # Finally, give the token a chance to react to it's own creation.

        token.on_add_to_world(self)

        info('adding token to world: {token}')
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

        # Don't reset the token's id (e.g. token._id = None) because we might 
        # need to undo this action and re-add the token to the world (e.g. if 
        # the server rejects the message that triggered this call).  In order 
        # to undo that action we need to know the token's original id number.

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

