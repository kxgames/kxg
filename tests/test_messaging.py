#!/usr/bin/env python

from test_helpers import *

class ReporterToken (DummyToken):

    def __init__(self, message):
        super().__init__()
        self.message = message

    @kxg.read_only
    def on_report_to_referee(self, reporter):
        if self.message:
            reporter.send_message(self.message)
            self.message = None


class DummyAcceptedMessage (DummyMessage):

    def on_check(self, world, sender):
        return True

    def on_sync(self, world, memento):
        raise AssertionError

    def on_undo(self, world):
        raise AssertionError


class DummyRejectedMessage (DummyMessage):

    expected_check_result = False

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
        world.undo_responses_handled.append(self)


class DummyUnhandledHardSyncError (DummySyncError):
    # Just a convenient alias.
    pass


class AddDummyToken (kxg.Message):

    def __init__(self, token=None):
        super().__init__()
        self.token = token or DummyToken()
        self.add_token(self.token)

    def on_check(self, world, sender_id):
        return True


class RemoveDummyToken (kxg.Message):

    def __init__(self, token):
        super().__init__()
        self.remove_token(token)

    def on_check(self, world, sender_id):
        return True



def add_dummy_token(actor, token=None):
    message = AddDummyToken(token)
    actor.send_message(message)
    return message.token

def remove_dummy_token(actor, token):
    message = RemoveDummyToken(token)
    actor.send_message(message)

def send_dummy_message(sender, message=None):
    message = message or DummyAcceptedMessage()
    assert sender.send_message(message) == message.expected_check_result
    return message


def test_messaging_reprs():
    message = kxg.Message(); message._set_server_response_id(1)
    assert kxg.ServerResponse(message).__repr__() == 'ServerResponse(sync_needed=False, undo_needed=False)'
    assert kxg.IdFactory(1, 4).__repr__() == 'IdFactory(offset=1, spacing=4)'

def test_message_serialization():
    import pickle

    original_message = DummyAcceptedMessage()
    packed_message = pickle.dumps(original_message)
    duplicate_message = pickle.loads(packed_message)

    assert b'tokens_to_add' not in packed_message
    assert b'tokens_to_remove' not in packed_message

    assert original_message.data == duplicate_message.data
    assert original_message.tokens_to_add == []
    assert original_message.tokens_to_remove == []


def test_uniplayer_message_sending():
    test = DummyUniplayerGame()
    messages = []

    # Make sure every actor can send and receive messages.

    for actor in test.actors:
        message = send_dummy_message(actor)
        messages.append(message)

        for observer in test.observers:
            assert observer.dummy_messages_received == messages
        assert test.world.dummy_messages_executed == messages

def test_uniplayer_message_rejection():
    test = DummyUniplayerGame()

    # Make sure that every actor will reject messages that fail the check.

    for actor in test.actors:
        send_dummy_message(actor, DummyRejectedMessage())

        for observer in test.observers:
            assert observer.dummy_messages_received == []
        assert test.world.dummy_messages_executed == []

def test_uniplayer_token_management():
    test = DummyUniplayerGame()

    # Add a token:

    token = add_dummy_token(test.random_actor)

    assert token in test.world

    # Remove a token:

    remove_dummy_token(test.random_actor, token)

    assert token not in test.world

def test_uniplayer_token_messaging():
    test = DummyUniplayerGame()

    # Make sure tokens can receive messages.

    token_1 = add_dummy_token(test.random_actor)
    message_1 = send_dummy_message(test.random_actor)

    for observer in token_1.observers:
        assert observer.dummy_messages_received == [message_1]

    # Make sure two tokens can receive messages.

    token_2 = add_dummy_token(test.random_actor)
    message_2 = send_dummy_message(test.random_actor)

    for observer in token_1.observers:
        assert observer.dummy_messages_received == [message_1, message_2]
    for observer in token_2.observers:
        assert observer.dummy_messages_received == [message_2]

def test_uniplayer_token_extension_messaging():
    test = DummyUniplayerGame()
    token = add_dummy_token(test.random_actor)
    messages = []

    # Make sure token extensions can send messages.

    for extension in token.get_extensions():
        message = send_dummy_message(extension)
        messages.append(message)

        assert message.was_sent_by(extension.actor)
        for observer in test.observers:
            assert observer.dummy_messages_received == messages
        assert test.world.dummy_messages_executed == messages

def test_uniplayer_reporter_messaging():
    test = DummyUniplayerGame()
    message = DummyAcceptedMessage()
    token = add_dummy_token(test.random_actor, ReporterToken(message))

    test.update()

    assert message.was_sent_by_referee()
    for observer in test.observers:
        assert observer.dummy_messages_received == [message]
    assert test.world.dummy_messages_executed == [message]

def test_uniplayer_was_sent_by():
    test = DummyUniplayerGame()

    # Make sure you can't ask who sent a message before it's sent.

    with raises_api_usage_error("can't ask who sent a message before it's been sent"):
        DummyAcceptedMessage().was_sent_by(test.random_actor)
    with raises_api_usage_error("can't ask who sent a message before it's been sent"):
        DummyAcceptedMessage().was_sent_by_referee()

    # Make sure Message.was_sent_by() works right.

    for sender in test.players:
        message = send_dummy_message(sender)

        assert not message.was_sent_by_referee()
        for actor in test.actors:
            assert message.was_sent_by(actor) == (actor is sender)

    # Make sure Message.was_sent_by_referee() works right.

    message = send_dummy_message(test.referee)

    assert message.was_sent_by_referee()
    for player in test.players:
        assert not message.was_sent_by(player)


def test_multiplayer_message_handling():
    test = DummyMultiplayerGame()

    message = send_dummy_message(test.client_actors[0])

    assert test.client_actors[0].messages_received == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]

    test.update()

    assert not message.was_sent_by_referee()
    assert message.was_sent_by(test.client_actors[0])
    assert not message.was_sent_by(test.client_actors[1])

    assert test.server_referee.messages_received == [message]
    assert test.server_world.messages_received == [message]
    assert test.server_world.messages_executed == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]

def test_multiplayer_message_rejection():
    test = DummyMultiplayerGame()
    message = DummyRejectedMessage()

    assert not test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == []
    assert test.client_actors[0].messages_received == []
    assert test.client_worlds[0].messages_executed == []

    test.update()

    assert test.server_referee.messages_received == []
    assert test.server_world.messages_received == []
    assert test.server_world.messages_executed == []
    assert test.client_actors[1].messages_received == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_worlds[1].messages_executed == []

def test_multiplayer_referee_messaging():
    test = DummyMultiplayerGame()
    message = DummyAcceptedMessage()

    assert test.server_referee.send_message(message)
    assert test.server_referee.messages_received == [message]
    assert test.server_world.messages_received == [message]
    assert test.server_world.messages_executed == [message]

    test.update()

    assert message.was_sent_by_referee()
    assert not message.was_sent_by(test.client_actors[0])
    assert not message.was_sent_by(test.client_actors[1])

    assert test.client_actors[0].messages_received == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]

def test_multiplayer_reporter_messaging():
    test = DummyMultiplayerGame()
    message = DummyAcceptedMessage()
    token = ReporterToken(message)

    force_add_token(test.server_world, token)
    test.update()

    assert message.was_sent_by_referee()

    assert test.server_referee.messages_received == [message]
    assert test.server_world.messages_executed == [message]
    assert test.server_world.messages_received == [message]
    assert test.client_actors[0].messages_received == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]

def test_multiplayer_sync_response():
    test = DummyMultiplayerGame()
    message = DummySoftSyncError()

    assert test.client_actors[0].send_message(message)
    assert test.client_actors[0].messages_received == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]

    test.update()

    assert test.server_referee.messages_received == [message]
    assert test.server_world.messages_received == [message]
    assert test.server_world.messages_executed == [message]
    assert test.client_actors[0].sync_responses_received == [message]
    assert test.client_worlds[0].sync_responses_received == [message]
    assert test.client_worlds[0].sync_responses_handled == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_actors[1].sync_responses_received == [message]
    assert test.client_worlds[1].sync_responses_handled == [message]
    assert test.client_worlds[1].sync_responses_received == [message]
    
def test_multiplayer_undo_response():
    test = DummyMultiplayerGame()
    message = DummyHardSyncError()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_referee.messages_received == []
    assert test.server_world.messages_received == []
    assert test.server_world.messages_executed == []
    assert test.client_actors[0].sync_responses_received == [message]
    assert test.client_worlds[0].sync_responses_received == [message]
    assert test.client_worlds[0].sync_responses_handled == [message]
    assert test.client_actors[0].undo_responses_received == [message]
    assert test.client_worlds[0].undo_responses_received == [message]
    assert test.client_worlds[0].undo_responses_handled == [message]
    assert test.client_actors[1].messages_received == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_worlds[1].messages_executed == []
    assert test.client_actors[1].sync_responses_received == []
    assert test.client_worlds[1].sync_responses_received == []
    assert test.client_worlds[1].sync_responses_handled == []
    assert test.client_actors[1].undo_responses_received == []
    assert test.client_worlds[1].undo_responses_received == []
    assert test.client_worlds[1].undo_responses_handled == []

def test_multiplayer_unhandled_undo_response():
    test = DummyMultiplayerGame()
    send_dummy_message(test.client_actors[0], DummyUnhandledHardSyncError())

    with raises_api_usage_error("the message", "was rejected by the server"):
        test.update()

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

def test_multiplayer_undo_token_creation():
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

def test_multiplayer_undo_token_destruction():
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

def test_unsubscribing_from_sync_responses():
    test = DummyMultiplayerGame()
    messages = [DummySoftSyncError() for i in range(3)]

    assert test.client_actors[0].sync_responses_received == []
    assert test.client_actors[1].sync_responses_received == []

    # Make sure soft errors can be handled.

    test.client_actors[1].send_message(messages[0])
    test.update()
    assert test.client_actors[0].sync_responses_received == messages[0:1]
    assert test.client_actors[1].sync_responses_received == messages[0:1]

    # Make sure soft errors can also be ignored.

    test.client_actors[1].unsubscribe_from_sync_response(DummyMessage)
    test.client_actors[1].send_message(messages[1])
    test.update()
    assert test.client_actors[0].sync_responses_received == messages[0:2]
    assert test.client_actors[1].sync_responses_received == messages[0:1]

    test.client_actors[0].send_message(messages[2])
    test.update()
    assert test.client_actors[0].sync_responses_received == messages[0:3]
    assert test.client_actors[1].sync_responses_received == messages[0:1]

def test_unsubscribing_from_undo_responses():
    test = DummyMultiplayerGame()
    messages = [DummyHardSyncError() for i in range(2)]

    assert test.client_actors[0].undo_responses_received == []
    assert test.client_actors[1].undo_responses_received == []

    # Make sure hard errors can be handled.

    test.client_actors[1].send_message(messages[0])
    test.update()
    assert test.client_actors[0].undo_responses_received == []
    assert test.client_actors[1].undo_responses_received == messages[0:1]

    # Make sure hard errors can also be ignored.

    test.client_actors[1].unsubscribe_from_undo_response(DummyMessage)
    test.client_actors[1].send_message(messages[1])
    test.update()
    assert test.client_actors[0].undo_responses_received == []
    assert test.client_actors[1].undo_responses_received == messages[0:1]


def test_cant_send_non_message():
    test = DummyUniplayerGame()

    with raises_api_usage_error('expected Message, but got str instead'):
        test.random_actor.send_message('not a message')

    with raises_api_usage_error('forgot to call the Message constructor in IncompleteMessage.__init__()'):
        class IncompleteMessage (kxg.Message):
            def __init__(self):
                pass
        test.random_actor.send_message(IncompleteMessage())

def test_cant_send_message_twice():
    test = DummyUniplayerGame()
    message = send_dummy_message(test.random_actor)

    with raises_api_usage_error("can't send the same message more than once"):
        test.random_actor.send_message(message)

def test_cant_use_stale_reporter():
    test = DummyUniplayerGame()

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


    add_dummy_token(test.referee, StaleReporterToken())

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

