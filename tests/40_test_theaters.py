import kxg
from test_helpers import *

class DummyStage (kxg.Stage):

    def __init__(self, num_updates=1):
        super().__init__()
        if num_updates == 'inf': num_updates = float('inf')
        self.num_updates = num_updates
        self.called_on_enter_stage = False
        self.called_on_update_stage = 0
        self.called_on_exit_stage = False

    def on_enter_stage(self):
        super().on_enter_stage()
        self.called_on_enter_stage = True
    
    def on_update_stage(self, dt):
        super().on_update_stage(dt)
        self.called_on_update_stage += 1
        if self.called_on_update_stage >= self.num_updates:
            self.exit_stage()
    
    def on_exit_stage(self):
        super().on_exit_stage()
        self.called_on_exit_stage = True



@pytest.yield_fixture
def logged_messages():
    import logging

    class UnitTestHandler (logging.Handler):

        def __init__(self):
            super().__init__()
            self.messages = []

        def emit(self, record):
            message = self.format(record)
            self.messages.append(message)
            print(message)


    handler = UnitTestHandler()
    handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(processName)s: %(name)s: %(message)s'))
    handler.setLevel(0)

    previous_level = logging.root.level
    logging.root.setLevel(0)
    logging.root.addHandler(handler)

    yield handler.messages

    logging.root.setLevel(previous_level)
    logging.root.removeHandler(handler)

def run_dummy_main(*command_lines):
    """
    Run the specified command lines in threads so that clients and servers 
    can talk to each other if they need to.  In some cases only one thread 
    will be started, but that's not a problem.  Use threads instead of 
    processes for the benefit of the code coverage analysis.  
    """
    import shlex

    with kxg.quickstart.ProcessPool(time_limit=4) as pool:
        for command_line in command_lines:
            name = '"{}"'.format(command_line)
            pool.start(name, dummy_main, shlex.split(command_line))

def log_something():
    kxg.info("Hello World!")

def raise_something():
    raise ZeroDivisionError

def sleep_forever():
    import time
    while True:
        time.sleep(1)


def test_stages():
    theater = kxg.Theater()
    theater.gui = "gui"

    stage_1 = DummyStage()
    stage_2 = DummyStage()
    stage_3 = DummyStage()

    theater.initial_stage = stage_1
    stage_1.successor = stage_2
    stage_2.successor = stage_3

    assert theater.initial_stage is stage_1
    assert not theater.is_finished

    theater.update()

    with raises_api_usage_error("theater already playing; can't set gui"):
        theater.gui = "new gui"
    
    assert theater.current_stage is stage_2
    assert theater.current_stage.gui == "gui"
    assert stage_1.called_on_enter_stage
    assert stage_1.called_on_update_stage
    assert stage_1.called_on_exit_stage
    assert stage_2.called_on_enter_stage
    assert not stage_2.called_on_update_stage
    assert not stage_2.called_on_exit_stage
    assert not stage_3.called_on_enter_stage
    assert not stage_3.called_on_update_stage
    assert not stage_3.called_on_exit_stage
    assert not theater.is_finished

    theater.update()

    assert theater.current_stage is stage_3
    assert theater.current_stage.gui == "gui"
    assert stage_1.called_on_enter_stage
    assert stage_1.called_on_update_stage
    assert stage_1.called_on_exit_stage
    assert stage_2.called_on_enter_stage
    assert stage_2.called_on_update_stage
    assert stage_2.called_on_exit_stage
    assert stage_3.called_on_enter_stage
    assert not stage_3.called_on_update_stage
    assert not stage_3.called_on_exit_stage
    assert not theater.is_finished

    theater.update()

    assert theater.current_stage is None
    assert stage_1.called_on_enter_stage
    assert stage_1.called_on_update_stage
    assert stage_1.called_on_exit_stage
    assert stage_2.called_on_enter_stage
    assert stage_2.called_on_update_stage
    assert stage_2.called_on_exit_stage
    assert stage_3.called_on_enter_stage
    assert stage_3.called_on_update_stage
    assert stage_3.called_on_exit_stage
    assert theater.is_finished

    with pytest.raises(AssertionError):
        theater.update()

def test_exit_stage():

    class ExitStage (kxg.Stage):

        def on_update_stage(self, dt):
            self.exit_theater()


    theater = kxg.Theater()
    theater.initial_stage = ExitStage()
    assert not theater.is_finished
    theater.update()
    assert theater.is_finished

def test_reset_initial_stage():
    theater = kxg.Theater()
    theater.initial_stage = DummyStage('inf')
    theater.update()

    with raises_api_usage_error():
        theater.initial_stage = DummyStage()

def test_uniplayer_game_stage():
    test = DummyUniplayerGame()
    test.update(10)
    test.referee >> DummyEndGameMessage()
    test.update()

    assert test.theater.is_finished

def test_multiplayer_game_stage():
    test = DummyMultiplayerGame()
    test.update(10)
    test.referee >> DummyEndGameMessage()
    test.update()

    # Make sure the multiplayer forums and actors play release their pipes once 
    # the game ends.  This test is a little gross because it has to reach into 
    # the internals of the pipe class.

    for client in test.clients:
        assert not client.pipe.serializer_stack
    for pipe in test.server.pipes:
        assert not pipe.serializer_stack

def test_quickstart_process_pool(logged_messages):
    # Make sure exceptions raised in worker processes are handled correctly.  
    # The exception should be re-raised in the main process and all the other 
    # workers should be immediately terminated.

    with pytest.raises(ZeroDivisionError):
        with kxg.quickstart.ProcessPool() as pool:
            pool.start("sleep forever", sleep_forever)
            pool.start("exception test", raise_something)

    # Make sure that the pool can shut down processes after they've gone over 
    # their time limit.

    with pytest.raises(RuntimeError):
        with kxg.quickstart.ProcessPool(time_limit=0.1) as pool:
            pool.start("sleep forever", sleep_forever)

    # Make sure that log messages made in the worker processes are correctly 
    # relayed to the main process.

    with kxg.quickstart.ProcessPool() as pool:
        pool.start("logging test", log_something)

    assert 'INFO: logging test: 40_test_theaters.log_something: Hello World!' in logged_messages

@pytest.mark.skip
def test_quickstart_sandbox(logged_messages):
    run_dummy_main('sandbox -v 1')
    assert 'INFO: "sandbox -v 1": test_helpers.DummyEndGameReferee: sending a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: "sandbox -v 1": kxg.forums.Forum: executing a message: DummyEndGameMessage()' in logged_messages

def test_quickstart_client_server(logged_messages):
    run_dummy_main('server 1 1 -v', 'client -v')
    assert 'INFO: "server 1 1 -v": test_helpers.DummyEndGameReferee: sending a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: "client -v": kxg.multiplayer.ClientForum: receiving a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: "server 1 1 -v": kxg.forums.Forum: executing a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: "client -v": kxg.multiplayer.ClientForum: executing a message: DummyEndGameMessage()' in logged_messages

def test_quickstart_debug(logged_messages):
    run_dummy_main('debug 2')
    assert 'INFO: Server: test_helpers.DummyEndGameReferee: sending a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: Server: kxg.forums.Forum: executing a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: Client #1: kxg.multiplayer.ClientForum: receiving a message: DummyEndGameMessage()' in logged_messages
    assert 'INFO: Client #1: kxg.multiplayer.ClientForum: executing a message: DummyEndGameMessage()' in logged_messages

