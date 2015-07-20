import kxg
import pytest, contextlib
import linersock.test_helpers
from pprint import pprint

class DummyUniplayerGame:

    def __init__(self):
        # Setup up a uniplayer game.

        self.world = DummyWorld()
        self.referee = DummyReferee()
        self.actors = [DummyActor(), DummyActor()]
        self.game_stage = kxg.UniplayerGameStage(
                self.world, self.referee, self.actors)
        self.game_stage.on_enter_stage()

        # Add a token to the world.
        
        self.token = DummyToken()
        self.token._give_id(self.referee._id_factory)

        force_add_token(self.world, self.token)

    def update(self, num_updates=1):
        for i in range(num_updates):
            self.game_stage.on_update_stage(0.1)


class DummyMultiplayerGame:

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

        # Add a token to the game (without sending a message).

        from copy import deepcopy
        token = DummyToken()
        token._give_id(self.server_referee._id_factory)

        self.server_token = deepcopy(token)
        force_add_token(self.server_world, self.server_token)

        self.client_tokens = []
        for client_world in self.client_worlds:
            client_token = deepcopy(token)
            force_add_token(client_world, client_token)
            self.client_tokens.append(client_token)

    def update(self, num_updates=2):
        for i in range(num_updates):
            for game_stage in self.client_game_stages:
                game_stage.on_update_stage(0.1)
            self.server_game_stage.on_update_stage(0.1)


class DummyMessage (kxg.Message, linersock.test_helpers.Message):

    def on_execute(self, world):
        world.messages_executed.append(self)

    def on_sync(self, world, memento):
        world.sync_responses_handled.append(self)


class DummyObserver:
    
    def __init__(self):
        super().__init__()
        self.messages_received = []
        self.sync_responses_received = []
        self.undo_responses_received = []

    @kxg.subscribe_to_message(DummyMessage)
    def on_dummy_message(self, message):
        self.messages_received.append(message)

    @kxg.subscribe_to_sync_response(DummyMessage)
    def on_sync_dummy_message(self, message):
        self.sync_responses_received.append(message)

    @kxg.subscribe_to_undo_response(DummyMessage)
    def on_undo_dummy_message(self, message):
        self.undo_responses_received.append(message)


class DummyActor (kxg.Actor, DummyObserver):

    def __init__(self, num_updates_before_finished=None):
        super().__init__()
        self.num_updates_before_finished = num_updates_before_finished
        self.num_updates = 0

    def on_update_game(self, dt):
        self.num_updates += 1

    def is_finished(self):
        return isinstance(self.num_updates_before_finished, int) and \
                self.num_updates >= self.num_updates_before_finished


class DummyReferee (kxg.Referee, DummyObserver):
    pass

class DummyWorld (kxg.World, DummyObserver):

    def __init__(self):
        super().__init__()
        self.messages_executed = []
        self.sync_responses_handled = []
        self.undo_responses_handled = []

    @kxg.read_only
    def has_game_ended(self):
        return False


class DummyToken (kxg.Token, DummyObserver):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

    def __str__(self):
        return '<DummyToken>'

    def __extend__(self):
        return {DummyActor: DummyExtension}

    @kxg.read_only
    def read_only(self):
        pass

    def read_write(self):
        pass

    @kxg.before_world
    def before_world(self):
        pass


class DummyExtension (kxg.TokenExtension, DummyObserver):
    pass


@contextlib.contextmanager
def raises_api_usage_error(*key_phrase_or_phrases):
    with pytest.raises(kxg.ApiUsageError) as exc:
        yield exc
    for key_phrase in key_phrase_or_phrases:
        assert key_phrase in exc.exconly().replace('\n', ' ')

def force_add_token(world, token, id=None):
    if id is not None:
        token._id = id
    elif token._id is None:
        token._id = len(world)

    with world._unlock_temporarily():
        world._add_token(token)

def force_remove_token(world, token):
    with world._unlock_temporarily():
        world._remove_token(token)
