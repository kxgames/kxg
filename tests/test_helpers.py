import kxg
import pytest, contextlib
import linersock.test_helpers
from pprint import pprint
import random; random.seed(0)

class DummyUniplayerGame:

    def __init__(self):
        # Setup up a uniplayer game.

        self.world = DummyWorld()
        self.referee = DummyReferee()
        self.players = [DummyActor(), DummyActor()]
        self.game_stage = kxg.UniplayerGameStage(
                self.world, self.referee, self.players)

        # Start playing the game.

        self.theater = kxg.Theater(self.game_stage)
        self.update()

    def update(self, num_updates=1):
        for i in range(num_updates):
            self.theater.update(0.1)

    @property
    def actors(self):
        yield self.referee
        yield from self.players

    @property
    def random_actor(self):
        self.last_random_actor = random.choice(list(self.actors))
        return self.last_random_actor

    @property
    def observers(self):
        yield from self.actors
        yield self.world
        for token in self.world:
            yield from token.observers


class DummyMultiplayerGame:

    def __init__(self, num_players=2):
        # Create the client and server stages.

        client_pipes, server_pipes = \
                linersock.test_helpers.make_pipes(num_players)

        self.client_worlds = [DummyWorld() for i in range(num_players)]
        self.client_actors = [DummyActor() for i in range(num_players)]
        self.client_theaters = [
                kxg.Theater(
                    kxg.MultiplayerClientGameStage(world, actor, pipe))
                for world, actor, pipe in zip(
                    self.client_worlds, self.client_actors, client_pipes)
        ]
        self.server_world = DummyWorld()
        self.server_referee = DummyReferee()
        self.server_theater = kxg.Theater(
                kxg.MultiplayerServerGameStage(
                    self.server_world, self.server_referee, server_pipes))

        # Wait for each client to get an id from the server.

        while not all(
                isinstance(theater.current_stage, kxg.GameStage)
                for theater in self.client_theaters):
            self.update()

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
            self.server_theater.update(0.1)
            for client_theater in self.client_theaters:
                client_theater.update(0.1)

    def assert_messages_received(self, messages):
        pass

    def assert_messages_received_locally(self, messages):
        pass


class DummyMessage (kxg.Message, linersock.test_helpers.Message):

    expected_check_result = True

    def on_execute(self, world):
        world.dummy_messages_executed.append(self)

    def on_sync(self, world, memento):
        world.dummy_sync_responses_handled.append(self)


class DummyObserver:
    
    def __init__(self):
        super().__init__()
        self.dummy_messages_received = []
        self.dummy_sync_responses_received = []
        self.dummy_undo_responses_received = []

    @kxg.subscribe_to_message(DummyMessage)
    def on_dummy_message(self, message):
        self.dummy_messages_received.append(message)

    @kxg.subscribe_to_sync_response(DummyMessage)
    def on_sync_dummy_message(self, message):
        self.dummy_sync_responses_received.append(message)

    @kxg.subscribe_to_undo_response(DummyMessage)
    def on_undo_dummy_message(self, message):
        self.dummy_undo_responses_received.append(message)


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
        self.dummy_messages_executed = []
        self.dummy_sync_responses_handled = []
        self.dummy_undo_responses_handled = []

    @kxg.read_only
    def has_game_ended(self):
        return False

    def received_dummy_messages(self, messages):
        assert super().received_dummy_messages(messages)
        assert self._dummy_messages
        assert self._dummy_messages_received == messages
        assert self._dummy_messages_received == messages
        return True

    def received_dummy_sync_responses(self, messages):
        assert self._dummy_sync_responses_received == messages
        return True

    def received_dummy_undo_responses(self, messages):
        assert self._dummy_undo_responses_received == messages
        return True

class DummyToken (kxg.Token, DummyObserver):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

    def __str__(self):
        return '<DummyToken>'

    def __extend__(self):
        return {DummyActor: DummyExtension}

    @property
    def observers(self):
        yield self
        yield from self.get_extensions()

    @kxg.before_world
    def before_world(self):
        pass

    @kxg.read_only
    def read_only(self):
        pass

    def read_write(self):
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

