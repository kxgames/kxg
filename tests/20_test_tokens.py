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
    expired_token = DummyToken(); \
            force_add_token(world, expired_token); \
            force_remove_token(world, expired_token)
    uninitialized_token = UninitializedTokenClass()
    non_token = NonTokenClass()

    kxg.require_token(active_token)
    kxg.require_token(pending_token)
    kxg.require_token(pending_with_id_token)
    kxg.require_token(expired_token)

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
        kxg.require_active_token(expired_token)
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
    world = DummyWorld()

    with world._unlock_temporarily():
        world._set_actors([actor])

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
            self.read_only_calls = 0
            self.read_write_calls = 0

        @kxg.watch_token
        def safe_method(self, x):
            self.read_only_calls += 1

        @kxg.watch_token
        def unsafe_method(self, x):
            self.read_write_calls += 1


    token_1 = WatchMethodToken()
    force_add_token(world, token_1)
    extension_1 = token_1.get_extension(actor)

    assert extension_1.read_only_calls == 0
    assert extension_1.read_write_calls == 0
    assert token_1.get_extensions() == [extension_1]

    token_1.safe_method(0)
    assert extension_1.read_only_calls == 1
    assert extension_1.read_write_calls == 0

    with world._unlock_temporarily():
        token_1.unsafe_method(0)
    assert extension_1.read_only_calls == 1
    assert extension_1.read_write_calls == 1
    
def test_cant_pickle_world():
    import pickle
    world = DummyWorld()

    with raises_api_usage_error("can't pickle the world"):
        pickle.dumps(world)

