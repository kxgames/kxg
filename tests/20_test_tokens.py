#!/usr/bin/env python

import kxg
from test_helpers import *

def force_add_token(world, token, id=None):
    if id is not None:
        token._id = id
    elif token._id is None:
        token._id = len(world)

    world._add_token(token)

def force_remove_token(world, token):
    world._remove_token(token)


class NonTokenClass:
    pass

class UninitializedTokenClass(DummyToken):
    def __init__(self):
        pass


def test_token_repr():
    assert DummyWorld().__repr__() == 'DummyWorld()'
    assert DummyToken().__repr__() == 'DummyToken(id=None)'

def test_token_creation():
    world = DummyWorld()
    token = DummyToken()

    # Make sure you can't add a non-token to the world.

    with raises_api_usage_error("expected Token, but got NonTokenClass instead"):
        world._add_token(NonTokenClass())

    # Make sure the game engine give a helpful error message when you 
    # forget to call Token.__init__() in a Token subclass.
    
    with raises_api_usage_error("forgot to call the Token constructor"):
        world._add_token(UninitializedTokenClass())

    # Make sure you can't add a token without an id to the world.

    with raises_api_usage_error("should have an id, but doesn't"):
        world._add_token(token)

    # Make sure Token._give_id() rejects raw id numbers.

    with raises_api_usage_error("can't use 1 as a token id"):
        token._give_id(1)

    # Make sure the token can actually be added to the world.

    force_add_token(world, token)

    # Make sure you can't assign the token an id twice.

    with raises_api_usage_error("already has an id"):
        token._give_id(kxg.IdFactory(1, 1))

    # Make sure you can't add the same token to the world twice.

    with raises_api_usage_error("can't add the same token to the world twice"):
        world._add_token(token)

    # Make sure you can't add a token that's been previously removed from 
    # the game.

    force_remove_token(world, token)

    with raises_api_usage_error("token DummyToken has been removed from the world"):
        force_add_token(world, token)

def test_token_type_checking():
    world = DummyWorld()
    pending_token = DummyToken()
    pending_with_id_token = DummyToken(); \
            pending_with_id_token._id = 1
    active_token = DummyToken(); \
            force_add_token(world, active_token)
    removed_token = DummyToken(); \
            force_add_token(world, removed_token); \
            force_remove_token(world, removed_token)
    uninitialized_token = UninitializedTokenClass()
    non_token = NonTokenClass()

    kxg.require_token(active_token)
    kxg.require_token(pending_token)
    kxg.require_token(pending_with_id_token)
    kxg.require_token(removed_token)

    with raises_api_usage_error("forgot to call the Token constructor"):
        kxg.require_token(uninitialized_token)
    with raises_api_usage_error("expected Token, but got NonTokenClass"):
        kxg.require_token(non_token)

    kxg.require_active_token(active_token)

    with raises_api_usage_error("should have an id, but doesn't"):
        kxg.require_active_token(pending_token)
    with raises_api_usage_error("not in world"):
        kxg.require_active_token(pending_with_id_token)
    with raises_api_usage_error("has been removed from the world"):
        kxg.require_active_token(removed_token)
    with raises_api_usage_error("forgot to call the Token constructor"):
        kxg.require_token(uninitialized_token)
    with raises_api_usage_error("expected Token, but got NonTokenClass"):
        kxg.require_token(non_token)

def test_token_participation():
    world = DummyWorld()
    token = DummyToken()

    # Make sure that tokens are in the 'pending' state before they're added to 
    # the world, and that 'pending' tokens can't be reset.

    assert token.world_participation == 'pending'
    with raises_api_usage_error("can't be reset because it's still being used"):
        token.reset_participation()

    # Make sure that tokens are in the 'active' state after they've been added 
    # to the world, and that 'active' tokens can't be reset.

    force_add_token(world, token)

    assert token.world_participation == 'active'
    with raises_api_usage_error("can't be reset because it's still being used"):
        token.reset_participation()

    # Make sure that tokens are in the 'removed' state after they've been 
    # removed from the world.

    force_remove_token(world, token)
    assert token.world_participation == 'removed'

    # Make sure that tokens can be reused once they've been reset.

    token.reset_participation()

    assert token.world_participation == 'pending'
    with raises_api_usage_error("can't be reset because it's still being used"):
        token.reset_participation()

    force_add_token(world, token)

    assert token.world_participation == 'active'
    with raises_api_usage_error("can't be reset because it's still being used"):
        token.reset_participation()

    force_remove_token(world, token)

def test_token_serialization():
    world = DummyWorld()
    token_1 = DummyToken(); force_add_token(world, token_1)
    token_2 = DummyToken(parent=token_1)
    token_2.attribute = "blue"

    serializer = kxg.TokenSerializer(world)
    deserializer = kxg.TokenSerializer(world)

    # Test the serialization of a registered token.  This should not create a 
    # copy of the original city object.

    packed_token_1 = serializer.pack(token_1)
    duplicate_token_1 = deserializer.unpack(packed_token_1)

    assert duplicate_token_1 is token_1

    # Test the serialization of an unregistered token.  This should result in 
    # two child tokens that both point to the same parent token.

    packed_token_2 = serializer.pack(token_2)
    duplicate_token_2 = deserializer.unpack(packed_token_2)

    assert duplicate_token_2 is not token_2
    assert duplicate_token_2.parent is token_2.parent
    assert duplicate_token_2.attribute == token_2.attribute

    # Test the serialization of a token that was previously registered with the 
    # world, but has since been removed.  This should result in a useful error:

    token_3 = DummyToken()
    force_add_token(world, token_3)
    force_remove_token(world, token_3)

    with raises_api_usage_error("has been removed from the world"):
        serializer.pack(token_3)

    # Test the serialization of a message object.  This should not result in 
    # the parent token being copied.

    message = kxg.Message()
    message.token = token_2
    packed_message = serializer.pack(message)
    duplicate_message = deserializer.unpack(packed_message)

    assert duplicate_message.token is not message.token
    assert duplicate_message.token.parent is message.token.parent
    assert duplicate_message.token.attribute == message.token.attribute

    # Ensure that both the original token and its clone can both subscribe 
    # callbacks still.

    force_add_token(world, token_2)

    token_1.subscribe_to_message(DummyMessage, lambda x: None)
    token_2.subscribe_to_message(DummyMessage, lambda x: None)

def test_token_extensions():
    actor = DummyActor()
    world = DummyWorld(); world._set_actors([actor])

    # Make sure a nice error is raised if the user forgets to write an 
    # appropriate constructor for their extension class.

    class BadConstructorToken (DummyToken):

        def __extend__(self):
            return {DummyActor: BadConstructorExtension}

    class BadConstructorExtension (DummyExtension):

        def __init__(self):
            pass


    with raises_api_usage_error("the BadConstructorExtension constructor doesn't take the right arguments."):
        force_add_token(world, BadConstructorToken())

    # Make sure a nice error is raised if the user tries to attach a callback 
    # to a token method that doesn't exist.

    class NoSuchMethodToken (DummyToken):

        def __extend__(self):
            return {DummyActor: NoSuchMethodExtension}

    class NoSuchMethodExtension (DummyExtension):

        @kxg.watch_token
        def no_such_method(self):
            pass


    with raises_api_usage_error('NoSuchMethodToken has no such method no_such_method() to watch'):
        force_add_token(world, NoSuchMethodToken())

    # Make sure extensions can attach callbacks to any widget method.

    class WatchMethodToken (DummyToken):

        def __extend__(self):
            return {DummyActor: WatchMethodExtension}

    class WatchMethodExtension (DummyExtension):

        def __init__(self, actor, token):
            super().__init__(actor, token)
            self.method_1_calls = []
            self.method_2_calls = []

        @kxg.watch_token
        def dummy_method_1(self, *args, **kwargs):
            self.method_1_calls.append((args, kwargs))

        @kxg.watch_token
        def dummy_method_2(self, *args, **kwargs):
            self.method_2_calls.append((args, kwargs))


    token_1 = WatchMethodToken()
    force_add_token(world, token_1)
    extension_1 = token_1.get_extension(actor)

    assert extension_1.method_1_calls == []
    assert extension_1.method_2_calls == []
    assert token_1.get_extensions() == [extension_1]

    token_1.dummy_method_1(1, a=2)
    assert extension_1.method_1_calls == [((1,),{'a':2})]
    assert extension_1.method_2_calls == []

    token_1.dummy_method_2(3, b=4)
    assert extension_1.method_1_calls == [((1,),{'a':2})]
    assert extension_1.method_2_calls == [((3,),{'b':4})]

    token_1.dummy_method_1(5, 6)
    assert extension_1.method_1_calls == [((1,),{'a':2}), ((5,6),{})]
    assert extension_1.method_2_calls == [((3,),{'b':4})]

    token_1.dummy_method_2(7, 8)
    assert extension_1.method_1_calls == [((1,),{'a':2}), ((5,6),{})]
    assert extension_1.method_2_calls == [((3,),{'b':4}), ((7,8),{})]

def test_cant_pickle_world():
    import pickle
    world = DummyWorld()

    with raises_api_usage_error("can't pickle the world"):
        pickle.dumps(world)

