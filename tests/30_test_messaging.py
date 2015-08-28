#!/usr/bin/env python

from test_helpers import *

# Things to test
# ==============
# 1. Rejecting bad add/remove token requests.
# 2. Trying harder to trick the undo machinery.

class TriggerResponse:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pass_check = True

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state
        self.pass_check = False

    def on_check(self, world):
        if not self.pass_check:
            raise kxg.MessageCheck


class DummyAcceptedMessage (DummyMessage):

    def on_check(self, world):
        pass

    def on_sync(self, world, memento):
        raise AssertionError

    def on_undo(self, world):
        raise AssertionError


class DummyRejectedMessage (DummyMessage):

    expected_check_result = False

    def on_check(self, world):
        raise kxg.MessageCheck

    def on_execute(self, world):
        raise AssertionError

    def on_sync(self, world, memento):
        raise AssertionError

    def on_undo(self, world):
        raise AssertionError


class DummySyncResponse (TriggerResponse, DummyMessage):

    def on_prepare_sync(self, world, memento):
        return True

    def on_undo(self, world):
        raise AssertionError


class DummyUndoResponse (TriggerResponse, DummyMessage):

    def on_undo(self, world):
        world.dummy_undo_responses_executed.append(self)


class DummyUnhandledUndoResponse (TriggerResponse, DummyMessage):
    # Just a convenient alias.
    pass

class NonDummyMessage (kxg.Message):
    pass

class AddDummyToken (kxg.Message):

    def __init__(self, token):
        self.token = token

    def tokens_to_add(self):
        yield self.token

    def on_check(self, world):
        pass


class AddDummyTokenAndSync (TriggerResponse, AddDummyToken):
    
    def on_prepare_sync(self, world, memento):
        return True


class AddDummyTokenAndUndo (TriggerResponse, AddDummyToken):
    
    def on_undo(self, world):
        pass


class RemoveDummyToken (kxg.Message):

    def __init__(self, token):
        self.token = token

    def tokens_to_remove(self):
        yield self.token

    def on_check(self, world):
        pass


class RemoveDummyTokenAndSync (TriggerResponse, RemoveDummyToken):
    
    def on_prepare_sync(self, world, memento):
        return True


class RemoveDummyTokenAndUndo (TriggerResponse, RemoveDummyToken):
    
    def on_undo(self, world):
        pass


class ReporterToken (DummyToken):

    def __init__(self, message):
        super().__init__()
        self.message = message

    @kxg.read_only
    def on_report_to_referee(self, reporter):
        if self.message:
            assert reporter >> self.message
            self.message = None



def add_dummy_token(actor, token=None, response=None):
    token = token or DummyToken()

    if response == None:
        message = AddDummyToken(token)
    elif response == 'sync':
        message = AddDummyTokenAndSync(token)
    elif response == 'undo':
        message = AddDummyTokenAndUndo(token)
    else:
        raise ValueError("unknown response '{}'".format(response))

    actor.send_message(message)
    return token

def remove_dummy_token(actor, token, response=None):
    if response == None:
        message = RemoveDummyToken(token)
    elif response == 'sync':
        message = RemoveDummyTokenAndSync(token)
    elif response == 'undo':
        message = RemoveDummyTokenAndUndo(token)
    else:
        raise ValueError("unknown response '{}'".format(response))

    actor.send_message(message)

def send_dummy_message(sender, message=None, response=None):
    if response == None:
        message = message or DummyAcceptedMessage()
    elif response == 'sync':
        message = DummySyncResponse()
    elif response == 'undo':
        message = DummyUndoResponse()
    else:
        raise ValueError("unknown response '{}'".format(response))

    assert (sender >> message) == message.expected_check_result
    return message


def test_id_factory():
    id = kxg.IdFactory(2, 3)

    assert repr(id) == 'IdFactory(offset=2, spacing=3)'

    assert id.get() == 2
    assert id.next() == 2
    assert id.next() == 5
    assert id.next() == 8

    assert 0 not in id
    assert 1 not in id
    assert 2 in id
    assert 3 not in id
    assert 4 not in id
    assert 5 in id

def test_messaging_reprs():
    message = kxg.Message(); message._set_server_response_id(1)
    assert kxg.ServerResponse(message).__repr__() == 'ServerResponse(sync_needed=False, undo_needed=False)'

def test_message_serialization():
    import pickle

    original_message = DummyAcceptedMessage()
    packed_message = pickle.dumps(original_message)
    duplicate_message = pickle.loads(packed_message)

    assert original_message.data == duplicate_message.data

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

        # Make sure the rejected message raise an exception.

        with pytest.raises(kxg.MessageCheck):
            send_dummy_message(actor, DummyRejectedMessage())

        # Make sure the rejected messages don't affect the game world

        for observer in test.observers:
            assert observer.dummy_messages_received == []
        assert test.world.dummy_messages_executed == []

def test_uniplayer_token_management():
    test = DummyUniplayerGame()

    for actor in test.actors:
        # Add a token to the game...

        token = add_dummy_token(actor)
        assert token in test.world

        # ...then remove it.

        remove_dummy_token(actor, token)
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

    for sender in test.dummy_actors:
        message = send_dummy_message(sender)

        assert not message.was_sent_by_referee()
        for actor in test.actors:
            assert message.was_sent_by(actor) == (actor is sender)

    # Make sure Message.was_sent_by_referee() works right.

    message = send_dummy_message(test.referee)

    assert message.was_sent_by_referee()
    for actor in test.dummy_actors:
        assert not message.was_sent_by(actor)

def test_multiplayer_message_sending():
    test = DummyMultiplayerGame()
    messages = []

    # Make sure every actor in every instance of the game can send and receive 
    # messages.

    for part_i in test.participants:
        for actor in part_i.actors:
            message = send_dummy_message(actor)
            messages.append(message)

            # Observers running in the same theater as the sender should 
            # receive the message immediately.

            for observer in part_i.observers:
                assert observer.dummy_messages_received == messages
            assert part_i.world.dummy_messages_executed == messages

            # Observers running in remote theaters should receive the message 
            # after an update.

            test.update()

            for part_j in test.participants:
                for observer in part_j.observers:
                    assert observer.dummy_messages_received == messages
                assert part_j.world.dummy_messages_executed == messages

def test_multiplayer_message_rejection():
    test = DummyMultiplayerGame()

    for part_i in test.participants:
        for actor in part_i.actors:

            # Send a message that should be rejected out of hand by the sender.

            with pytest.raises(kxg.MessageCheck):
                send_dummy_message(actor, DummyRejectedMessage())

            test.update()

            # Make sure none of the actors receive the message.

            for part_j in test.participants:
                for observer in part_j.observers:
                    assert observer.dummy_messages_received == []
                assert part_j.world.dummy_messages_executed == []

def test_multiplayer_sync_response():
    """
    Test sending messages that will trigger "sync" responses form the server.
    
    The messages must be sent from a client (the server is always in sync with 
    itself), pass the check on the client, then fail the check on the server.  
    The server then must decide the relay the messages in spite of their 
    failure to pass the check, along with a request for the clients to take the 
    opportunity to resynchronize.  The server does all this in the interest of 
    keeping the gameplay responsive if the failure is not severe.
    """
    test = DummyMultiplayerGame()
    messages = []

    for client in test.clients:
        for actor in client.actors:
            message = send_dummy_message(actor, response='sync')
            messages.append(message)

            # Make sure the message is handled like usual by the sender.

            for observer in client.observers:
                assert observer.dummy_messages_received == messages
            assert client.world.dummy_messages_executed == messages

            # Make sure the server relays the message to all the other 
            # observers participating in the game.

            test.update()

            for observer in test.observers:
                assert observer.dummy_messages_received == messages
            for world in test.worlds:
                assert world.dummy_messages_executed == messages

            # Make sure the clients are instructed to sync up.

            for observer in test.client_observers:
                assert observer.dummy_sync_responses_received == messages
            for world in test.client_worlds:
                assert world.dummy_sync_responses_executed == messages

def test_multiplayer_undo_response():
    """
    Test sending messages that will trigger "undo" responses from the server.

    The messages must be sent from a client (the server will never undo its own 
    message), pass the check on the client, then fail the check on the server.  
    If the server doesn't decide that the failure is recoverable, it will not 
    relay the message and will instruct the client that sent it to undo it.
    """
    test = DummyMultiplayerGame()

    for client in test.clients:
        for actor in client.actors:
            message = send_dummy_message(actor, DummyUndoResponse())

            # Make sure the message is handled like usual by the sender.

            for observer in client.observers:
                assert observer.dummy_messages_received == [message]
            assert client.world.dummy_messages_executed == [message]

            # Make sure the server doesn't relay the message.

            test.update()

            remote_participants = (
                    x for x in test.participants
                    if x is not client)

            for participant in remote_participants:
                for observer in participant.observers:
                    assert message not in observer.dummy_messages_received
                assert message not in participant.world.dummy_messages_executed

            # Make sure the sender is instructed to undo its message.

            for observer in client.observers:
                assert observer.dummy_undo_responses_received == [message]
            assert client.world.dummy_undo_responses_executed == [message]

def test_multiplayer_unhandled_undo_response():
    test = DummyMultiplayerGame()
    send_dummy_message(test.random_client_actor, DummyUnhandledUndoResponse())

    with raises_api_usage_error("the message", "was rejected by the server"):
        test.update()

def test_multiplayer_malicious_sender_id(capsys):
    # Make sure the server rejects messages that claim to be from the wrong 
    # player.  This is mostly to prevent cheating, although I suppose it's also 
    # a debugging feature.

    test = DummyMultiplayerGame()
    fake_id = kxg.IdFactory(0,1)

    for cheater in test.clients:
        message = DummyMessage()
        message._set_sender_id(fake_id)

        cheater.pipe.send(message)
        test.update()

        out, err = capsys.readouterr()
        assert "ignoring message from player {} claiming to be from player 0".format(cheater.gui_actor.id) in err

        for observer in test.observers:
            assert observer.dummy_messages_received == []
        for world in test.worlds:
            assert world.dummy_messages_executed == []

def test_multiplayer_token_management():
    test = DummyMultiplayerGame()

    for actor in test.actors:
        # Add a token to the game...

        token = add_dummy_token(actor)
        test.update()

        for world in test.worlds:
            assert token in world

        # ...then remove it.

        remove_dummy_token(actor, token)
        test.update()

        for world in test.worlds:
            assert token not in world

def test_multiplayer_token_messaging():
    test = DummyMultiplayerGame()
    token = add_dummy_token(test.random_actor)
    messages = []

    for actor in test.actors:
        message = send_dummy_message(actor)
        messages.append(message)
        test.update()

        for observer in token.observers:
            assert observer.dummy_messages_received == messages

def test_multiplayer_undo_token_creation():
    test = DummyMultiplayerGame()

    for client in test.clients:
        for actor in client.actors:
            token = add_dummy_token(actor, response='undo')

            # Make sure the token is created by the sender.

            assert token in client.world

            # Make sure the token is removed from all the worlds once its 
            # creation has been rejected by the server.

            test.update()

            for world in test.worlds:
                assert token not in world

def test_multiplayer_undo_token_destruction():
    test = DummyMultiplayerGame()

    for client in test.clients:
        for actor in client.actors:
            # Add a token to the game.

            token = add_dummy_token(actor)
            test.update()

            for world in test.worlds:
                assert token in world

            # Send a message (that will be undone) to remove the token.  Make sure 
            # the sender executes the message.

            remove_dummy_token(actor, token, response='undo')

            assert token not in client.world

            # Make sure the token is still present in all the worlds once its 
            # removal has been rejected by the server.

            test.update()

            for world in test.worlds:
                assert token in world

def test_multiplayer_reporter_messaging():
    test = DummyMultiplayerGame()
    message = DummyAcceptedMessage()
    token = ReporterToken(message)

    # Have to use the referee to add the reporter token to prevent its message 
    # from being pickled and deep copied.  This would break the was_sent_by() 
    # test below.

    add_dummy_token(test.server.referee, token)
    test.update()

    assert message.was_sent_by_referee()

    for observer in test.observers:
        assert observer.dummy_messages_received == [message]
    for world in test.worlds:
        assert world.dummy_messages_executed == [message]

def test_multiplayer_was_sent_by():
    test = DummyMultiplayerGame()

    for sender in test.actors:
        send_dummy_message(sender)
        test.update()

        for actor in test.actors:
            received_message = actor.dummy_messages_received[-1]
            assert received_message.was_sent_by(sender)
            assert received_message.was_sent_by_referee() == isinstance(
                    sender, kxg.Referee)

def test_subscribing_to_multiple_messages():
    test = DummyUniplayerGame()

    class Message1 (DummyAcceptedMessage):
        pass

    class Message2 (DummyAcceptedMessage):
        pass

    class Message3 (DummyAcceptedMessage):
        pass

    class ListeningToken (kxg.Token):

        def on_add_to_world(self, world):
            self.messages = []

        @kxg.subscribe_to_message(Message1)
        @kxg.subscribe_to_message(Message2)
        def on_either_message(self, message):
            self.messages.append(message)


    token = ListeningToken()
    message_1 = Message1()
    message_2 = Message2()
    message_3 = Message3()

    add_dummy_token(test.random_actor, token)

    test.random_actor >> message_1
    assert token.messages == [message_1]

    test.random_actor >> message_2
    assert token.messages == [message_1, message_2]

    test.random_actor >> message_3
    assert token.messages == [message_1, message_2]

def test_unsubscribing_from_messages():
    test = DummyUniplayerGame()

    # Add a token to the test so that we will also test unsubscribing for 
    # tokens and token extensions.
    
    token = add_dummy_token(test.random_actor)
    assert token in test.observers

    for observer in test.observers:
        # Test unsubscribing from an unrelated message class.  The handler 
        # should still be called.

        observer.unsubscribe_from_message(NonDummyMessage)
        message_1 = send_dummy_message(test.random_actor)

        assert message_1 in observer.dummy_messages_received

        # Test unsubscribing from the message class being sent.  The handler 
        # should not be called.

        observer.unsubscribe_from_message(DummyMessage)
        message_2 = send_dummy_message(test.random_actor)

        assert message_2 not in observer.dummy_messages_received

def test_unsubscribing_from_sync_responses():
    test = DummyMultiplayerGame()

    # Add a token to the test so that we will also test unsubscribing for 
    # tokens and token extensions.
    
    token = add_dummy_token(test.random_actor); test.update()
    for world in test.client_worlds: assert token in world

    for observer in test.client_observers:
        # Test unsubscribing from an unrelated message class.  The handler 
        # should still be called.

        observer.unsubscribe_from_sync_response(NonDummyMessage)
        message_1 = send_dummy_message(test.random_client_actor, response='sync')
        test.update()

        assert message_1 in observer.dummy_messages_received
        assert message_1 in observer.dummy_sync_responses_received

        # Test unsubscribing from the message class being sent.  The handler 
        # should not be called.

        observer.unsubscribe_from_sync_response(DummyMessage)
        message_2 = send_dummy_message(test.random_client_actor, response='sync')
        test.update()

        assert message_2 in observer.dummy_messages_received
        assert message_2 not in observer.dummy_sync_responses_received

def test_unsubscribing_from_undo_responses():
    test = DummyMultiplayerGame()

    # Add a token to the test so that we will also test unsubscribing for 
    # tokens and token extensions.
    
    token = add_dummy_token(test.random_actor); test.update()
    for world in test.client_worlds: assert token in world

    for client in test.clients:
        for actor in client.actors:
            # Test unsubscribing from an unrelated message class.  The handler 
            # should still be called.

            actor.unsubscribe_from_undo_response(NonDummyMessage)
            message_1 = send_dummy_message(actor, response='undo')
            test.update()

            for observer in client.observers:
                assert message_1 in observer.dummy_messages_received
                assert message_1 in observer.dummy_sync_responses_received
                assert message_1 in observer.dummy_undo_responses_received

            # Test unsubscribing from the message class being sent.  The 
            # handler should not be called.

            actor.unsubscribe_from_undo_response(DummyMessage)
            message_2 = send_dummy_message(actor, response='undo')
            test.update()

            for observer in client.observers:
                assert message_2 in observer.dummy_messages_received
                assert message_2 in observer.dummy_sync_responses_received
                assert (message_2 in observer.dummy_undo_responses_received) == \
                        (observer is not actor)

def test_cant_send_non_message():
    test = DummyUniplayerGame()

    with raises_api_usage_error('expected Message, but got str instead'):
        test.random_actor.send_message('not a message')

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
        test.update()

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


