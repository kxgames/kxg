#!/usr/bin/env python

from utilities import *

class DummyAcceptedMessage (DummyMessage):

    def on_check(self, world, sender):
        return True

    def on_sync(self, world, memento):
        raise AssertionError

    def on_undo(self, world):
        raise AssertionError


class DummyRejectedMessage (DummyMessage):

    def on_check(self, world, sender):
        return False

    def on_execute(self, world):
        raise AssertionError

    def on_sync(self, world, memento):
        raise AssertionError

    def on_undo(self, world):
        raise AssertionError


class DummySyncError (DummyMessage):
    # In order to get a sync error, the message must pass the check on the 
    # client and fail it on the server.  The purpose of this class is to spoof 
    # this process.  Messages of this type will pass the check if they have 
    # never been pickled, and fail it after that.  This strategy triggers sync 
    # errors and allows the same message object to be used more than once.

    def __init__(self):
        super().__init__()
        self.pass_check = True

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state
        self.pass_check = False

    def on_check(self, world, sender_id):
        return self.pass_check


class DummySoftSyncError (DummySyncError):

    def on_prepare_sync(self, world, memento):
        return True

    def on_undo(self, world):
        raise AssertionError


class DummyHardSyncError (DummySyncError):

    def on_undo(self, world):
        world.hard_errors_handled.append(self)


class DummyUnhandledHardSyncError (DummySyncError):
    # Just a convenient alias.
    pass


def test_message_pickling():
    import pickle

    original_message = DummyAcceptedMessage()
    packed_message = pickle.dumps(original_message)
    duplicate_message = pickle.loads(packed_message)

    assert b'tokens_to_add' not in packed_message
    assert b'tokens_to_remove' not in packed_message

    assert original_message.data == duplicate_message.data
    assert original_message.tokens_to_add == []
    assert original_message.tokens_to_remove == []

def test_sending_non_message():
    test = DummyUniplayerGame()

    with raises_api_usage_error('expected Message, but got str instead'):
        test.referee.send_message('not a message')

    with raises_api_usage_error('forgot to call the Message constructor in IncompleteMessage.__init__()'):
        class IncompleteMessage (kxg.Message):
            def __init__(self):
                pass
        test.referee.send_message(IncompleteMessage())

def test_uniplayer_message_handling():
    test = DummyUniplayerGame()
    message = DummyAcceptedMessage()

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
    message = DummyRejectedMessage()

    assert not test.actors[0].send_message(message)
    assert test.world.messages_executed == []
    assert test.world.messages_received == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

def test_multiplayer_message_handling():
    test = DummyMultiplayerGame()
    message = DummyAcceptedMessage()

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
    message = DummyAcceptedMessage()

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
    message = DummyRejectedMessage()

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
    assert test.client_worlds[0].soft_errors_received == [message]
    assert test.client_worlds[0].soft_errors_handled == [message]
    assert test.client_actors[0].soft_errors_received == [message]
    assert test.client_worlds[0].hard_errors_received == [message]
    assert test.client_worlds[0].hard_errors_handled == [message]
    assert test.client_actors[0].hard_errors_received == [message]
    assert test.client_worlds[1].messages_executed == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_actors[1].messages_received == []
    assert test.client_worlds[1].soft_errors_received == []
    assert test.client_worlds[1].soft_errors_handled == []
    assert test.client_actors[1].soft_errors_received == []
    assert test.client_worlds[1].hard_errors_received == []
    assert test.client_worlds[1].hard_errors_handled == []
    assert test.client_actors[1].hard_errors_received == []

def test_uniplayer_token_management():
    # Add one token:

    test = DummyUniplayerGame()
    token = DummyToken()
    message = DummyAcceptedMessage()
    message.add_token(token)

    assert test.actors[0].send_message(message)
    assert token in test.world

    with raises_api_usage_error("can't add or remove tokens after"):
        message.add_token(token)

    # Remove one token:

    message = DummyAcceptedMessage()
    message.remove_token(token)

    assert test.actors[1].send_message(message)
    assert token not in test.world

    with raises_api_usage_error("can't add or remove tokens after"):
        message.remove_token(token)

    # Add two tokens:

    test = DummyUniplayerGame()
    tokens = DummyToken(), DummyToken()
    message = DummyAcceptedMessage()
    message.add_tokens(tokens)

    assert test.actors[1].send_message(message)
    assert all(x in test.world for x in tokens)

    with raises_api_usage_error("can't add or remove tokens after"):
        message.add_tokens(tokens)

    # Remove two tokens:

    message = DummyAcceptedMessage()
    message.remove_tokens(tokens)

    assert test.actors[0].send_message(message)
    assert all(x not in test.world for x in tokens)

    with raises_api_usage_error("can't add or remove tokens after"):
        message.add_tokens(tokens)

def test_multiplayer_token_creation():
    test = DummyMultiplayerGame()
    token = DummyToken()
    message = DummyAcceptedMessage()
    message.add_token(token)

    assert test.client_actors[1].send_message(message)
    assert token in test.client_worlds[1]

    test.update()

    assert token in test.server_world
    assert token in test.client_worlds[0]

def test_multiplayer_token_destruction():
    test = DummyMultiplayerGame()
    token = test.client_tokens[1]
    message = DummyAcceptedMessage()
    message.remove_token(token)

    assert len(test.client_worlds[1]) == 2
    assert test.client_actors[1].send_message(message)
    assert len(test.client_worlds[1]) == 1
    assert len(test.server_world) == 2
    assert len(test.client_worlds[0]) == 2

    test.update()

    assert len(test.server_world) == 1
    assert len(test.client_worlds[0]) == 1

def test_multiplayer_token_creation_with_hard_sync_error():
    test = DummyMultiplayerGame()
    token = DummyToken()
    message = DummyHardSyncError()
    message.add_token(token)

    assert token not in test.client_worlds[1]
    assert test.client_actors[1].send_message(message)

    assert token not in test.server_world
    assert token not in test.client_worlds[0]
    assert token in test.client_worlds[1]

    test.update()

    assert token not in test.server_world
    assert token not in test.client_worlds[0]
    assert token not in test.client_worlds[1]

def test_multiplayer_token_destruction_with_hard_sync_error():
    test = DummyMultiplayerGame()
    token = test.client_tokens[1]; id = token.id
    message = DummyHardSyncError()
    message.remove_token(token)

    assert id in test.server_world
    assert id in test.client_worlds[0]
    assert id in test.client_worlds[1]

    assert test.client_actors[1].send_message(message)

    assert id in test.server_world
    assert id in test.client_worlds[0]
    assert id not in test.client_worlds[1]

    test.update()

    assert id in test.server_world
    assert id in test.client_worlds[0]
    assert id in test.client_worlds[1]

def test_unsubscribing_from_messages():
    test = DummyUniplayerGame()
    messages = [DummyAcceptedMessage() for i in range(2)]

    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

    # Test unsubscribing from an unrelated message class.  The handler should 
    # still be called.

    class UnrelatedMessage (kxg.Message): pass   # (no fold)

    test.actors[1].unsubscribe_from_message(UnrelatedMessage)
    test.actors[1].send_message(messages[0])

    assert test.actors[0].messages_received == messages[0:1]
    assert test.actors[1].messages_received == messages[0:1]

    # Test unsubscribing from the right message class.  This time the handler 
    # should not be called.

    test.actors[1].unsubscribe_from_message(DummyMessage)
    test.actors[1].send_message(messages[1])

    assert test.actors[0].messages_received == messages[0:2]
    assert test.actors[1].messages_received == messages[0:1]

def test_unsubscribing_from_soft_sync_errors():
    test = DummyMultiplayerGame()
    messages = [DummySoftSyncError() for i in range(3)]

    assert test.client_actors[0].soft_errors_received == []
    assert test.client_actors[1].soft_errors_received == []

    # Make sure soft errors can be handled.

    test.client_actors[1].send_message(messages[0])
    test.update()
    assert test.client_actors[0].soft_errors_received == messages[0:1]
    assert test.client_actors[1].soft_errors_received == messages[0:1]

    # Make sure soft errors can also be ignored.

    test.client_actors[1].unsubscribe_from_soft_sync_error(DummyMessage)
    test.client_actors[1].send_message(messages[1])
    test.update()
    assert test.client_actors[0].soft_errors_received == messages[0:2]
    assert test.client_actors[1].soft_errors_received == messages[0:1]

    test.client_actors[0].send_message(messages[2])
    test.update()
    assert test.client_actors[0].soft_errors_received == messages[0:3]
    assert test.client_actors[1].soft_errors_received == messages[0:1]

def test_unsubscribing_from_hard_sync_errors():
    test = DummyMultiplayerGame()
    messages = [DummyHardSyncError() for i in range(2)]

    assert test.client_actors[0].hard_errors_received == []
    assert test.client_actors[1].hard_errors_received == []

    # Make sure hard errors can be handled.

    test.client_actors[1].send_message(messages[0])
    test.update()
    assert test.client_actors[0].hard_errors_received == []
    assert test.client_actors[1].hard_errors_received == messages[0:1]

    # Make sure hard errors can also be ignored.

    test.client_actors[1].unsubscribe_from_hard_sync_error(DummyMessage)
    test.client_actors[1].send_message(messages[1])
    test.update()
    assert test.client_actors[0].hard_errors_received == []
    assert test.client_actors[1].hard_errors_received == messages[0:1]

def test_sending_from_token_extension():
    test = DummyUniplayerGame()
    message = DummyAcceptedMessage()

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

def test_cant_send_message_twice():
    test = DummyUniplayerGame()
    message = DummyAcceptedMessage()

    test.actors[0].send_message(message)
    with raises_api_usage_error("can't send the same message more than once"):
        test.actors[0].send_message(message)

def test_cant_use_stale_reporter():

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

    class AddStaleReporterToken (kxg.Message):

        def __init__(self):
            super().__init__()
            token = StaleReporterToken()
            self.add_token(token)


    test = DummyUniplayerGame()
    message = AddStaleReporterToken()
    test.actors[0].send_message(message)

    with raises_api_usage_error("DummyMessage message sent using a stale reporter"):
        test.update(1)

def test_cant_subscribe_to_non_message():
    test = DummyUniplayerGame()
    callback = lambda message: None

    with raises_api_usage_error("expected Message subclass, but got"):
        test.referee.subscribe_to_message("not a message", callback)
    with raises_api_usage_error("expected Message subclass, but got"):
        test.referee.subscribe_to_message(DummyMessage(), callback)

def test_cant_subscribe_in_token_ctor():

    class SubscribeInConstructorToken (DummyToken):

        def __init__(self):
            super().__init__()
            self.subscribe_to_message(DummyMessage, lambda message: None)


    with raises_api_usage_error("can't subscribe to messages now."):
        token = SubscribeInConstructorToken()

def test_unhandled_hard_sync_error():
    test = DummyMultiplayerGame()
    message = DummyUnhandledHardSyncError()
    assert test.client_actors[0].send_message(message)
    with raises_api_usage_error("the message", "was rejected by the server"):
        test.update()

