#!/usr/bin/env python

import kxg
from test_helpers import *

def test_token_repr():
    assert DummyToken().__repr__() == 'DummyToken(id=None)'
    assert DummyWorld().__repr__() == 'DummyWorld()'

def test_token_type_checking():
    world = DummyWorld()

    class UninitializedTokenClass(DummyToken):
        def __init__(self):
            pass

    class NonTokenClass:
        pass


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
    with raises_api_usage_error("should have an id, but doesn't"):
        kxg.require_active_token(removed_token)
    with raises_api_usage_error("forgot to call the Token constructor"):
        kxg.require_token(uninitialized_token)
    with raises_api_usage_error("expected Token, but got NonTokenClass"):
        kxg.require_token(non_token)

def test_token_safety_checking():
    from inspect import signature

    world = DummyWorld()
    token = DummyToken()

    # Make sure the original method's metadata is kept as the safety checks are 
    # added and removed.

    assert token.unsafe_method.__name__ == 'unsafe_method'
    assert token.unsafe_method.__doc__ == """ Docstring. """
    assert str(signature(token.unsafe_method)) == '(x)'

    force_add_token(world, token)

    assert token.unsafe_method.__name__ == 'unsafe_method'
    assert token.unsafe_method.__doc__ == """ Docstring. """
    assert str(signature(token.unsafe_method)) == '(x)'

    force_remove_token(world, token)

    assert token.unsafe_method.__name__ == 'unsafe_method'
    assert token.unsafe_method.__doc__ == """ Docstring. """
    assert str(signature(token.unsafe_method)) == '(x)'

    # Make sure "unsafe" methods can't be called if the token has been added to 
    # the world and the world hasn't been unlocked.  Also make sure the safety 
    # checks can be added and removed (as the token itself is added and removed 
    # from the world) more than once.
    
    def assert_safety_checks_off(token):
        token.safe_method(1)
        token.unsafe_method(2)
        token.safe_super_method(3)
        token.unsafe_super_method(4)
        token.safe_property = 5
        token.safe_property

    def assert_safety_checks_on(token):
        token.safe_method(1)
        with raises_api_usage_error("unsafe invocation", "DummyToken.unsafe_method()"):
            token.unsafe_method(2)
        token.safe_super_method(3)
        with raises_api_usage_error("unsafe invocation", "DummyToken.unsafe_super_method()"):
            token.unsafe_super_method(4)
        token.safe_property = 5
        token.safe_property


    # Run the test twice to make sure the safety checks aren't affected by the 
    # token entering and exiting the world.

    for i in range(2):
        assert_safety_checks_off(token)

        force_add_token(world, token)
        assert_safety_checks_on(token)

        with world._unlock_temporarily():
            assert_safety_checks_off(token)

            # Make sure that nested calls to unlock_temporarily() don't lock 
            # the world prematurely.

            with world._unlock_temporarily(): pass
            assert_safety_checks_off(token)

        force_remove_token(world, token)
        assert_safety_checks_off(token)

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

        @kxg.read_only
        def dummy_method_1(self, *args, **kwargs):
            pass

        @kxg.read_only
        def dummy_method_2(self, *args, **kwargs):
            pass

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

