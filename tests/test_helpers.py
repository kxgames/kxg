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
        self.gui_actor = DummyActor()
        self.ai_actors = [DummyActor()]
        self.game_stage = kxg.UniplayerGameStage(
                self.world, self.referee, self.gui_actor, self.ai_actors)

        # Start playing the game.

        self.theater = kxg.Theater(self.game_stage)
        self.update()

    def update(self, num_updates=1):
        for i in range(num_updates):
            if not self.theater.is_finished:
                self.theater.update()

    @property
    def actors(self):
        yield self.referee
        yield from self.dummy_actors

    @property
    def dummy_actors(self):
        yield self.gui_actor
        yield from self.ai_actors

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

    class Client:

        def __init__(self, client_pipe):
            self.world = DummyWorld()
            self.gui_actor = DummyActor()
            self.pipe = client_pipe
            self.theater = kxg.Theater(
                    kxg.MultiplayerClientGameStage(
                        self.world, self.gui_actor, self.pipe))

        @property
        def actors(self):
            return [self.gui_actor]

        @property
        def observers(self):
            yield from self.actors
            yield self.world
            for token in self.world:
                yield from token.observers

    class Server:

        def __init__(self, server_pipes):
            self.world = DummyWorld()
            self.referee = DummyReferee()
            self.ai_actors = [DummyActor(), DummyActor()]
            self.pipes = server_pipes
            self.theater = kxg.Theater(
                    kxg.MultiplayerServerGameStage(
                        self.world, self.referee, self.ai_actors, self.pipes))

        @property
        def actors(self):
            return [self.referee] + self.ai_actors

        @property
        def observers(self):
            yield from self.actors
            yield self.world
            for token in self.world:
                yield from token.observers


    def __init__(self, num_players=2):
        # Create the server and a handful of clients.

        client_pipes, server_pipes = \
                linersock.test_helpers.make_pipes(num_players)

        self.server = DummyMultiplayerGame.Server(server_pipes)
        self.clients = [DummyMultiplayerGame.Client(p) for p in client_pipes]

        # Update all the clients once to make sure they can wait for an id.

        for client in self.clients:
            client.theater.update(0.1)

        # Give each client an id.

        self.update()

    @property
    def participants(self):
        return [self.server] + self.clients

    @property
    def observers(self):
        for participant in self.participants:
            yield from participant.observers

    @property
    def actors(self):
        for participant in self.participants:
            yield from participant.actors

    @property
    def referee(self):
        return self.server.referee

    @property
    def worlds(self):
        for participant in self.participants:
            yield participant.world

    @property
    def client_observers(self):
        for client in self.clients:
            yield from client.observers

    @property
    def client_actors(self):
        for client in self.clients:
            yield from client.actors

    @property
    def client_worlds(self):
        for client in self.clients:
            yield client.world

    @property
    def random_actor(self):
        self.last_random_actor = random.choice(list(self.actors))
        return self.last_random_actor

    @property
    def random_client_actor(self):
        self.last_random_actor = random.choice(list(self.client_actors))
        return self.last_random_actor

    def update(self, num_updates=2):
        import time
        for i in range(num_updates):
            for part in self.participants:
                if not part.theater.is_finished:
                    part.theater.update()
            time.sleep(1/60)


class DummyMessage (kxg.Message, linersock.test_helpers.Message):

    expected_check_result = True

    def on_execute(self, world):
        world.dummy_messages_executed.append(self)

    def on_sync(self, world, memento):
        world.dummy_sync_responses_executed.append(self)


class DummyEndGameMessage (kxg.Message):

    def on_check(self, world):
        pass

    def on_execute(self, world):
        world.end_game()


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

class DummyEndGameReferee (DummyReferee):

    def on_start_game(self, num_players):
        self >> DummyEndGameMessage()

        

class DummyWorld (kxg.World, DummyObserver):

    def __init__(self):
        super().__init__()
        self.dummy_messages_executed = []
        self.dummy_sync_responses_executed = []
        self.dummy_undo_responses_executed = []

    @kxg.read_only
    def has_game_ended(self):
        return False


class DummyToken (kxg.Token, DummyObserver):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

    def __str__(self):
        # Overwrite __str__() instead of __repr__() so that we can still test 
        # Token.__repr__().
        return self.__class__.__name__

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

class DummyGui:
    pass


def dummy_main(argv=None):
    kxg.quickstart.main(
            world_cls=DummyWorld,
            referee_cls=DummyEndGameReferee,
            gui_cls=DummyGui,
            gui_actor_cls=DummyActor,
            ai_actor_cls=DummyActor,
            argv=argv,

    )

@contextlib.contextmanager
def raises_api_usage_error(*key_phrase_or_phrases):
    with pytest.raises(kxg.ApiUsageError) as exc:
        yield exc
    for key_phrase in key_phrase_or_phrases:
        assert key_phrase in exc.exconly().replace('\n', ' ')

