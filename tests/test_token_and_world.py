#!/usr/bin/env python

import kxg
from dummies import *
from pprint import pprint

def test_cant_modify_token_if_world_locked():
    world = DummyWorld()
    token = DummyToken()
    world._add_token(token)

    # 1. Make sure 

def test_cant_modify_token_with_bad_id():
    world = DummyWorld()

    # This error is triggered if the token has a reference to the world but 
    # doesn't have a valid id.  I can think of two ways for this to happen 
    # (both of which would fall under the category of willful user error):
    
    # 1. The user resets the token's id sometime after adding it to the world.

    token = DummyToken()
    world._add_token(token)
    token._id = None

    with raises_api_usage_error():
        token.non_read_only()

    # 2. The user manually sets the token's world reference.

    token = DummyToken()
    token._world = world

    with raises_api_usage_error():
        token.non_read_only()

def test_cant_modify_token_if_not_in_world():
    pass

def test_token_pickling():
    import pickle
    original_token = DummyToken()
    original_token.subscribe_to_message('asdasd', 'asdsad')
    pprint(original_token.__dict__)
    print()
    buffer = pickle.dumps(original_token)
    pickled_token = pickle.loads(buffer)
    print()
    pprint(pickled_token.__dict__)
    assert False

def test_cant_pickle_world():
    import pickle
    world = DummyWorld()

    with raises_api_usage_error("Can't pickle the world"):
        pickle.dumps(world)

def test_illegal_token_id():
    world = DummyWorld()
    null_token = DummyToken()
    non_int_token = DummyToken()
    non_int_token._id = 'what?'

    with raises_api_usage_error("Token <DummyToken> doesn't have an id"):
        world._add_token(null_token)

    with raises_api_usage_error("Token <DummyToken> has a non-integer"):
        world._add_token(non_int_token)

def test_illegal_token_access():
    world = DummyWorld()
    token = DummyToken()

    # Test illegal access before adding the token to the world.

    token.before_world()
    token.read_only()

    with raises_api_usage_error("unsafe invocation of DummyToken.read_write()"):
        token.read_write()

    # Test illegal access after adding the token to the world.

    token._id = 1
    world._add_token(token)

    with raises_api_usage_error("May have forgotten to add <DummyToken>"):
        token.before_world()

    token.read_only()
    token.read_write()

    # Test illegal access after removing the token from the world.

    world._remove_token(token)

    with raises_api_usage_error("May have forgotten to add <DummyToken>"):
        token.before_world()

    with raises_api_usage_error("unsafe invocation of DummyToken.read_write()"):
        token.read_write()

    token.read_only()

