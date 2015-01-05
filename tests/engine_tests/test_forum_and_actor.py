#!/usr/bin/env python

import kxg, finalexam
from helpers import *
from pprint import pprint

@finalexam.test
def test_uniplayer_message_handling():
    test = UniplayerTest()
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

@finalexam.test
def test_uniplayer_message_rejection():
    test = UniplayerTest()
    message = DummyMessage(False)

    assert not test.actors[0].send_message(message)
    assert test.world.messages_executed == []
    assert test.world.messages_received == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

@finalexam.test
def test_multiplayer_message_handling():
    test = MultiplayerTest()
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

@finalexam.test
def test_multiplayer_referee_messaging():
    test = MultiplayerTest()
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

@finalexam.test
def test_multiplayer_message_rejection():
    test = MultiplayerTest()
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

@finalexam.test
def test_multiplayer_soft_sync_error_handling():
    test = MultiplayerTest()
    message = SoftSyncError()

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
    
@finalexam.test
def test_multiplayer_hard_sync_error_handling():
    test = MultiplayerTest()
    message = HardSyncError()

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

@finalexam.test
def test_uniplayer_token_creation():
    test = UniplayerTest()
    token = DummyToken()
    message = kxg.CreateToken(token)

    assert test.actors[0].send_message(message)
    assert token in test.world

@finalexam.test
def test_uniplayer_token_destruction():
    test = UniplayerTest()
    message = kxg.DestroyToken(test.token)

    assert test.token in test.world
    assert test.actors[0].send_message(message)
    assert test.token not in test.world

@finalexam.test
def test_multiplayer_token_creation():
    test = MultiplayerTest()
    token = DummyToken()
    message = kxg.CreateToken(token)

    assert test.client_actors[0].send_message(message)
    assert token in test.client_worlds[0]

    test.update()

    assert token in test.server_world
    assert token in test.client_worlds[1]

@finalexam.test
def test_multiplayer_token_destruction():
    test = MultiplayerTest()
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

@finalexam.skip
def test_multiplayer_token_creation_with_hard_sync_error():
    pass

@finalexam.skip
def test_multiplayer_token_destruction_with_hard_sync_error():
    pass

@finalexam.test
def test_stale_reporter_error():

    class StaleReporterToken (kxg.Token):

        def __init__(self):
            super().__init__()
            self.reporter = None

        def on_report_to_referee(self, reporter):
            self.reporter = reporter

        def on_update_game(self, dt):
            if self.reporter:
                self.reporter.send_message(DummyMessage())


    test = UniplayerTest()
    token = StaleReporterToken()
    message = kxg.CreateToken(token)
    test.actors[0].send_message(message)

    with finalexam.expect(kxg.StaleReporterError):
        test.update(1)


if __name__ == '__main__':
    finalexam.title("Testing the forum and the actors...")
    finalexam.run()
