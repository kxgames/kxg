#!/usr/bin/env python

import kxg
import finalexam
import linersock.test_helpers

class UniplayerTest:

    def __init__(self):
        self.world = DummyWorld()
        self.referee = DummyReferee()
        self.actors = [DummyActor(), DummyActor()]
        self.game_stage = kxg.UniplayerGameStage(
                self.world, self.referee, self.actors)
        self.game_stage.on_enter_stage()

    def update(self, num_updates=1):
        self.game_stage.on_update_stage(0.1)


class MultiplayerTest:

    def __init__(self):
        # Create the client and server stages.

        client_pipes, server_pipes = linersock.test_helpers.make_pipes(2)

        self.client_worlds = [DummyWorld(), DummyWorld()]
        self.client_actors = [DummyActor(), DummyActor()]
        self.client_connection_stages = [
                kxg.MultiplayerClientGameStage(
                    self.client_worlds[0], self.client_actors[0], client_pipes[0]),
                kxg.MultiplayerClientGameStage(
                    self.client_worlds[1], self.client_actors[1], client_pipes[1]),
        ]

        self.server_world = DummyWorld()
        self.server_referee = DummyReferee()
        self.server_game_stage = kxg.MultiplayerServerGameStage(
                self.server_world, self.server_referee, server_pipes)

        # Wait for each client to get an id from the server.

        self.server_game_stage.on_enter_stage()
        self.client_game_stages = []

        for connection_stage in self.client_connection_stages:
            connection_stage.on_enter_stage()

            while not connection_stage.is_finished():
                connection_stage.on_update_stage(0.1)
                self.server_game_stage.on_update_stage(0.1)

            game_stage = connection_stage.get_successor()
            game_stage.on_enter_stage()

            self.client_game_stages.append(game_stage)

    def update(self, num_updates=2):
        for i in range(num_updates):
            for game_stage in self.client_game_stages:
                game_stage.on_update_stage(0.1)
            self.server_game_stage.on_update_stage(0.1)


class TestObserver:

    @property
    def messages_received(self):
        try:
            return self._messages_received
        except AttributeError:
            self._messages_received = []
            return self._messages_received

    @property
    def soft_errors_received(self):
        try:
            return self._soft_errors_received
        except AttributeError:
            self._soft_errors_received = []
            return self._soft_errors_received

    @property
    def hard_errors_received(self):
        try:
            return self._hard_errors_received
        except AttributeError:
            self._hard_errors_received = []
            return self._hard_errors_received

    @kxg.handle_message(kxg.Message)
    def on_handle_message(self, message):
        self.messages_received.append(message)

    @kxg.handle_soft_sync_error(kxg.Message)
    def on_handle_soft_sync_error(self, message):
        self.soft_errors_received.append(message)

    @kxg.handle_hard_sync_error(kxg.Message)
    def on_handle_hard_sync_error(self, message):
        self.hard_errors_received.append(message)


class DummyActor (kxg.Actor, TestObserver):
    pass

class DummyReferee (kxg.Referee, TestObserver):
    pass

class DummyWorld (kxg.World, TestObserver):

    def __init__(self):
        super().__init__()
        self.messages_executed = []
        self.soft_errors_handled = []
        self.hard_errors_handled = []

    @kxg.read_only
    def has_game_ended(self):
        return False


class DummyToken (kxg.Token, TestObserver):

    def __extend__(self):
        return {DummyActor: DummyExtension}


class DummyExtension (kxg.TokenExtension, TestObserver):
    pass

class DummyMessage (kxg.Message, linersock.test_helpers.Message):

    def __init__(self, pass_check=True):
        super().__init__()
        self.pass_check = pass_check

    def on_check(self, world, sender):
        return self.pass_check

    def on_execute(self, world):
        world.messages_executed.append(self)

    def on_soft_sync_error(self, world):
        raise AssertionError

    def on_hard_sync_error(self, world):
        raise AssertionError


class SoftSyncError (kxg.Message, linersock.test_helpers.Message):

    def __init__(self):
        super().__init__()
        self.check_result = True

    def on_check(self, world, sender_id):
        # Return True the first time, but False after that.
        retval = self.check_result
        self.check_result = False
        return retval

    def on_check_for_soft_sync_error(self, world):
        return True

    def on_execute(self, world):
        world.messages_executed.append(self)

    def on_soft_sync_error(self, world):
        world.soft_errors_handled.append(self)


class HardSyncError (kxg.Message, linersock.test_helpers.Message):

    def __init__(self):
        super().__init__()
        self.check_result = True

    def on_check(self, world, sender_id):
        # Return True the first time, but False after that.
        retval = self.check_result
        self.check_result = False
        return retval

    def on_check_for_soft_sync_error(self, world):
        return False

    def on_execute(self, world):
        world.messages_executed.append(self)

    def on_soft_sync_error(self, world):
        raise AssertionError

    def on_hard_sync_error(self, world):
        world.hard_errors_handled.append(self)



@finalexam.test
def test_uniplayer_message_handling():
    test = UniplayerTest()
    message = DummyMessage()

    assert test.actors[0].send_message(message)
    assert test.world.messages_received == [message]
    assert test.world.messages_executed == [message]
    assert test.referee.messages_received == [message]
    assert test.actors[0].messages_received == [message]
    assert test.actors[1].messages_received == [message]

@finalexam.test
def test_uniplayer_message_rejection():
    test = UniplayerTest()
    message = DummyMessage(False)

    assert not test.actors[0].send_message(message)
    assert test.world.messages_received == []
    assert test.world.messages_executed == []
    assert test.actors[0].messages_received == []
    assert test.actors[1].messages_received == []

@finalexam.test
def test_multiplayer_message_handling():
    test = MultiplayerTest()
    message = DummyMessage()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_received == [message]
    assert test.server_world.messages_executed == [message]
    assert test.server_referee.messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_actors[1].messages_received == [message]

@finalexam.test
def test_multiplayer_referee_messaging():
    test = MultiplayerTest()
    message = DummyMessage()

    assert test.server_referee.send_message(message)
    assert test.server_world.messages_received == [message]
    assert test.server_world.messages_executed == [message]
    assert test.server_referee.messages_received == [message]

    test.update()

    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_actors[0].messages_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_actors[1].messages_received == [message]

@finalexam.test
def test_multiplayer_message_rejection():
    test = MultiplayerTest()
    message = DummyMessage(False)

    assert not test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == []
    assert test.client_worlds[0].messages_executed == []
    assert test.client_actors[0].messages_received == []

    test.update()

    assert test.server_world.messages_received == []
    assert test.server_world.messages_executed == []
    assert test.server_referee.messages_received == []
    assert test.client_worlds[1].messages_received == []
    assert test.client_worlds[1].messages_executed == []
    assert test.client_actors[1].messages_received == []

@finalexam.test
def test_multiplayer_soft_fail_error_handling():
    test = MultiplayerTest()
    message = SoftSyncError()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_received == [message]
    assert test.server_world.messages_executed == [message]
    assert test.server_referee.messages_received == [message]
    assert test.client_worlds[0].soft_errors_received == [message]
    assert test.client_worlds[0].soft_errors_handled == [message]
    assert test.client_actors[0].soft_errors_received == [message]
    assert test.client_worlds[1].messages_received == [message]
    assert test.client_worlds[1].messages_executed == [message]
    assert test.client_actors[1].messages_received == [message]
    assert test.client_worlds[1].soft_errors_received == [message]
    assert test.client_worlds[1].soft_errors_handled == [message]
    assert test.client_actors[1].soft_errors_received == [message]
    
@finalexam.test
def test_multiplayer_hard_fail_error_handling():
    test = MultiplayerTest()
    message = HardSyncError()

    assert test.client_actors[0].send_message(message)
    assert test.client_worlds[0].messages_received == [message]
    assert test.client_worlds[0].messages_executed == [message]
    assert test.client_actors[0].messages_received == [message]

    test.update()

    assert test.server_world.messages_received == []
    assert test.server_world.messages_executed == []
    assert test.server_referee.messages_received == []
    assert test.client_worlds[0].hard_errors_received == [message]
    assert test.client_worlds[0].hard_errors_handled == [message]
    assert test.client_actors[0].hard_errors_received == [message]
    assert test.client_worlds[1].messages_received == []
    assert test.client_worlds[1].messages_executed == []
    assert test.client_actors[1].messages_received == []

@finalexam.skip
def test_stale_reporter_error():

    class StaleReporterToken (kxg.Token):

        def __init__(self):
            self.reporter = None

        def report(self, reporter):
            self.reporter = reporter

        def update(self, dt):
            if self.reporter:
                self.reporter.send_message(NormalMessage())


    test = UniplayerTest()
    test.add_token(StaleReporterToken())

    with finalexam.expect(kxg.StaleReporterError):
        test.update()


if __name__ == '__main__':
    finalexam.title("Testing the forum and the actors...")
    finalexam.run()
