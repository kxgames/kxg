#!/usr/bin/env python

import kxg
import testing

# Expecting these names to be defined:
#   UniplayerTest
#   MultiplayerTest
#   NormalMessage
#   SoftFailMessage
#   HardFailMessage
#   InstantFailMessage

@testing.test
def test_uniplayer_normal_message_handling():
    test = UniplayerTest()
    message = NormalMessage()

    assert test.actors[0].send_message(message)
    assert test.world.messages_received == [message]
    assert test.actors[0].messages_received == [message]
    assert test.actors[1].messages_received == [message]

@testing.test
def test_uniplayer_instant_fail_message_handling():
    test = UniplayerTest()
    message = InstantFailMessage()

    assert not test.actors[0].send_message(message)
    assert test.world.messages_received == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

@testing.test
def test_multiplayer_normal_message_handling():
    test = MultiplayerTest()
    message = NormalMessage()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_received == [message]
    assert test.server_actor.messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_actors[1].messages_received == [message]

@testing.test
def test_multiplayer_soft_fail_message_handling():
    test = MultiplayerTest()
    message = SoftFailMessage()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_received == [message]
    assert test.server_actor.messages_received == [message]
    assert test.server_world.soft_fails_received == [message]
    assert test.server_actor.soft_fails_received == [message]
    assert test.client_worlds[0].soft_fails_received == [message]
    assert test.client_actors[0].soft_fails_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].soft_fails_received == [message]
    assert test.client_actors[1].soft_fails_received == [message]
    
@testing.test
def test_multiplayer_hard_fail_message_handling():
    test = MultiplayerTest()
    message = HardFailMessage()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_received == []
    assert test.server_actor.messages_received == []
    assert test.client_worlds[0].hard_fails_received == [message]
    assert test.client_actors[0].hard_fails_received == [message]
    assert test.client_worlds[1].messages_received == []
    assert test.client_actors[1].messages_received == []

@testing.test
def test_multiplayer_instant_fail_message_handling():
    test = MultiplayerTest()
    message = InstantFailMessage()

    assert not test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == []
    assert test.client_actors[0].messages_received == []

    test.update()

    assert test.server_world.messages_received == []
    assert test.server_actor.messages_received == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_actors[1].messages_received == []


