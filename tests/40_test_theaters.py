import kxg
from test_helpers import *

# Things to test
# ==============
# 1. Rejecting bad add/remove token requests.
# 2. Trying harder to trick the undo machinery.
# 3. Quickstart.

class DummyStage (kxg.Stage):

    def __init__(self, num_updates=1):
        super().__init__()
        if num_updates == 'inf': num_updates = float('inf')
        self.num_updates = num_updates
        self.called_on_enter_stage = False
        self.called_on_update_stage = 0
        self.called_on_exit_stage = False

    def on_enter_stage(self):
        self.called_on_enter_stage = True
    
    def on_update_stage(self, dt):
        self.called_on_update_stage += 1
        if self.called_on_update_stage >= self.num_updates:
            self.exit_stage()
    
    def on_exit_stage(self):
        self.called_on_exit_stage = True


class DummyEndGame (kxg.Message):

    def on_check(self, world, sender_id):
        return True

    def on_execute(self, world):
        world.end_game()


class DummyEndGameActor (kxg.Actor):

    def on_start_game(self):
        self >> DummyEndGame()



def run_quickstart_main(*command_lines):
    """
    Run the specified command lines in threads so that clients and servers 
    can talk to each other if they need to.  In some cases only one thread 
    will be started, but that's not a problem.  Use threads instead of 
    processes for the benefit of the code coverage analysis.  
    """
    import queue, shlex
    from concurrent.futures import ThreadPoolExecutor

    # Catch any exceptions thrown in worker threads and forward them to the 
    # main thread via a thread-safe queue.  If this isn't done, the exceptions 
    # would be ignored.  This obviously makes debugging a nightmare.

    exceptions = queue.Queue()

    def main(i=0):
        try:
            kxg.quickstart.main(
                    world_cls=DummyWorld,
                    referee_cls=DummyReferee,
                    gui_actor_cls=DummyEndGameActor,
                    ai_actor_cls=DummyActor,
                    argv=shlex.split(command_lines[i]),
            )
        except Exception as exception:
            exceptions.put(exception)


    # Run the given command lines.  If more than one command line was given, 
    # spawn threads to execute them all at once, otherwise they'll get hung up 
    # waiting for each other.  If only one command line was given, execute it 
    # without spawning any threads.

    if len(command_lines) == 1:
        main()
    else:
        with ThreadPoolExecutor(len(command_lines)) as executor:
            for i in range(len(command_lines)):
                executor.submit(main, i)

            print(executor._threads)

    # Re-raise any exceptions originally raised in the worker threads.

    try: raise exceptions.get_nowait()
    except queue.Empty: pass


def test_stages():
    theater = kxg.Theater()
    stages = DummyStage(), DummyStage(), DummyStage()

    for i in range(len(stages) - 1):
        stages[i].successor = stages[i+1]

    theater.initial_stage = stages[0]
    assert theater.initial_stage is stages[0]

    for i in range(len(stages)):
        if i > 0:
            assert theater.current_stage is stages[i]

        theater.update(0.1)

        for stage in stages[:i+1]:
            assert stage.called_on_enter_stage
            assert stage.called_on_update_stage
            assert stage.called_on_exit_stage

        for i, stage in enumerate(stages[i+1:]):
            assert stage.called_on_enter_stage == (i == 0)
            assert not stage.called_on_update_stage
            assert not stage.called_on_exit_stage

    assert theater.is_finished

def test_exit_stage():

    class ExitStage (kxg.Stage):

        def on_update_stage(self, dt):
            self.exit_theater()


    theater = kxg.Theater()
    theater.initial_stage = ExitStage()
    theater.update(0.1)
    assert theater.is_finished

def test_reset_initial_stage():
    theater = kxg.Theater()
    theater.initial_stage = DummyStage('inf')
    theater.update(0.1)

    with raises_api_usage_error():
        theater.initial_stage = DummyStage()

    theater.initial_stage.exit_theater()
    theater.update(0.1)

    assert theater.is_finished
    theater.initial_stage = DummyStage()
    assert not theater.is_finished

def test_pyglet_theater():
    theater = kxg.PygletTheater()
    theater.initial_stage = DummyStage()
    theater.play()

def test_uniplayer_game_stage():
    # The engine doesn't really do anything when the game ends, so this is 
    # really just a test to make sure nothing crashes.

    test = DummyUniplayerGame()
    test.update(10)
    test.referee.send_message(DummyEndGame())
    test.update(10)

    assert test.theater.is_finished

def test_multiplayer_game_stage():
    test = DummyMultiplayerGame()
    test.update(10)
    test.referee.send_message(DummyEndGame())
    test.update(10)

    # Make sure the multiplayer forums and actors play release their pipes once 
    # the game ends.  This test is a little gross because it has to reach into 
    # the internals of the pipe class.

    for client in test.clients:
        assert not client.pipe.serializer_stack
    for pipe in test.server.pipes:
        assert not pipe.serializer_stack

def test_quickstart_main(capfd):
    """
    Make sure that quickstart.main() runs without crashing.  The only 
    assertion, made inside run_quickstart_main(), makes sure that the game 
    actually ran and wasn't skipped somehow.  Issues with the game itself 
    should've been caught by previous tests.
    """
    run_quickstart_main('sandbox -v')

    out, err = capfd.readouterr()
    assert 'INFO: kxg.actors.DummyEndGameActor: sending a message: DummyEndGame()' in err
    assert 'INFO: kxg.forums.Forum: executing a message: DummyEndGame()' in err

    run_quickstart_main('server 2', 'client', 'client')

    out, err = capfd.readouterr()
    assert 'INFO: kxg.actors.DummyEndGameActor: sending a message: DummyEndGame()' in err
    assert 'INFO: kxg.multiplayer.ServerActor: received a message: DummyEndGame()' in err
    assert 'INFO: kxg.forums.ClientForum: executing a message: DummyEndGame()' in err

    run_quickstart_main('debug 1')

