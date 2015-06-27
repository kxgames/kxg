#!/usr/bin/env python

import kxg
from utilities import *
from pprint import pprint

def test_uniplayer_message_handling():
    test = DummyUniplayerGame()
    message = DummyMessage()

    assert test.world.messages_executed == []
    assert test.world.messages_received == []
    assert test.token.messages_received == []
    assert test.referee.messages_received == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

    assert test.actors[0].send_message(message)

    assert test.world.messages_executed == [message]
    assert test.world.messages_received == [message]
    assert test.token.messages_received == [message]
    assert test.referee.messages_received == [message]
    assert test.actors[0].messages_received == [message]
    assert test.actors[1].messages_received == [message]

def test_uniplayer_message_rejection():
    test = DummyUniplayerGame()
    message = DummyMessage(False)

    assert not test.actors[0].send_message(message)
    assert test.world.messages_executed == []
    assert test.world.messages_received == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

def test_multiplayer_message_handling():
    test = DummyMultiplayerGame()
    message = DummyMessage()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_executed == [message]
    assert test.server_world.messages_received == [message]
    assert test.server_referee.messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_actors[1].messages_received == [message]

def test_multiplayer_referee_messaging():
    test = DummyMultiplayerGame()
    message = DummyMessage()

    assert test.server_referee.send_message(message)
    assert test.server_world.messages_executed == [message]
    assert test.server_world.messages_received == [message]
    assert test.server_referee.messages_received == [message]

    test.update()

    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_actors[1].messages_received == [message]

def test_multiplayer_message_rejection():
    test = DummyMultiplayerGame()
    message = DummyMessage(False)

    assert not test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_executed == []
    assert test.client_worlds[0].messages_received == []
    assert test.client_actors[0].messages_received == []

    test.update()

    assert test.server_world.messages_executed == []
    assert test.server_world.messages_received == []
    assert test.server_referee.messages_received == []
    assert test.client_worlds[1].messages_executed == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_actors[1].messages_received == []

def test_multiplayer_soft_sync_error_handling():
    test = DummyMultiplayerGame()
    message = DummySoftSyncError()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_executed == [message]
    assert test.server_world.messages_received == [message]
    assert test.server_referee.messages_received == [message]
    assert test.client_worlds[0].soft_errors_received == [message]
    assert test.client_worlds[0].soft_errors_handled == [message]
    assert test.client_actors[0].soft_errors_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].soft_errors_received == [message]
    assert test.client_worlds[1].soft_errors_handled == [message]
    assert test.client_actors[1].soft_errors_received == [message]
    
def test_multiplayer_hard_sync_error_handling():
    test = DummyMultiplayerGame()
    message = DummyHardSyncError()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_executed == []
    assert test.server_world.messages_received == []
    assert test.server_referee.messages_received == []
    assert test.client_worlds[0].hard_errors_received == [message]
    assert test.client_worlds[0].hard_errors_handled == [message]
    assert test.client_actors[0].hard_errors_received == [message]
    assert test.client_worlds[1].messages_executed == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_actors[1].messages_received == []

def test_uniplayer_token_creation():
    test = DummyUniplayerGame()
    token = DummyToken()
    message = kxg.CreateToken(token)

    assert test.actors[0].send_message(message)
    assert token in test.world

def test_uniplayer_token_destruction():
    test = DummyUniplayerGame()
    message = kxg.DestroyToken(test.token)

    assert test.token in test.world
    assert test.actors[0].send_message(message)
    assert test.token not in test.world

def test_multiplayer_token_creation():
    test = DummyMultiplayerGame()
    token = DummyToken()
    message = kxg.CreateToken(token)

    assert test.client_actors[0].send_message(message)
    assert token in test.client_worlds[0]

    test.update()

    assert token in test.server_world
    assert token in test.client_worlds[1]

def test_multiplayer_token_destruction():
    test = DummyMultiplayerGame()
    token = test.client_tokens[0]
    message = kxg.DestroyToken(token)

    assert len(test.client_worlds[0]) == 2
    assert test.client_actors[0].send_message(message)
    assert len(test.client_worlds[0]) == 1
    assert len(test.server_world) == 2
    assert len(test.client_worlds[1]) == 2

    test.update()

    assert len(test.server_world) == 1
    assert len(test.client_worlds[1]) == 1

def test_multiplayer_token_creation_with_hard_sync_error():
    pass

def test_multiplayer_token_destruction_with_hard_sync_error():
    pass

def test_sending_from_token_extension():
    test = DummyUniplayerGame()
    message = DummyMessage()

    assert test.world.messages_executed == []
    assert test.world.messages_received == []
    assert test.token.messages_received == []
    assert test.referee.messages_received == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

    assert test.token.get_extension(test.actors[0]).send_message(message)

    assert test.world.messages_executed == [message]
    assert test.world.messages_received == [message]
    assert test.token.messages_received == [message]
    assert test.referee.messages_received == [message]
    assert test.actors[0].messages_received == [message]
    assert test.actors[1].messages_received == [message]

def test_stale_reporter_error():

    class StaleReporterToken (kxg.Token):

        def __init__(self):
            super().__init__()
            self.reporter = None

        @kxg.read_only
        def on_report_to_referee(self, reporter):
            self.reporter = reporter

        def on_update_game(self, dt):
            if self.reporter:
                self.reporter.send_message(DummyMessage())


    test = DummyUniplayerGame()
    token = StaleReporterToken()
    message = kxg.CreateToken(token)
    test.actors[0].send_message(message)

    with raises_api_usage_error("DummyMessage message sent using a stale reporter"):
        test.update(1)


