#!/usr/bin/env python3

import linersock
from .errors import *
from .theater import *

default_host = 'localhost'
default_port = 53351

class ClientConnectionStage (Stage):

    def __init__(self, world, gui_actor, host, port):
        super().__init__()
        self.world = world
        self.gui_actor = gui_actor
        self.host = host
        self.port = port
        self.pipe = None
        self.client = linersock.Client(
                host, port, callback=self.on_connection_established)

    def on_enter_stage(self):
        print("kxg client connecting to {}:{}".format(self.host, self.port))

    def on_update_stage(self, time):
        self.client.connect()

    def on_connection_established(self, pipe):
        self.pipe = pipe
        self.exit_stage()

    def on_exit_stage(self):
        game_stage = MultiplayerClientGameStage(
                self.world, self.gui_actor, self.pipe)
        game_stage.successor.successor = PostgameSplashStage()
        self.successor = game_stage


class ServerConnectionStage (Stage):

    def __init__(self, world, referee, num_clients, ai_actors=[], host=default_host, port=default_port):
        super().__init__()
        self.world = world
        self.referee = referee
        self.ai_actors = ai_actors
        self.host = host
        self.port = port
        self.pipes = []
        self.greetings = []
        self.server = linersock.Server(
                host, port, num_clients, self.on_clients_connected)

    def on_enter_stage(self):
        print("kxg server running on {}:{}".format(self.host, self.port))
        self.server.open()

    def on_update_stage(self, dt):
        if not self.server.finished():
            self.server.accept()
        else:
            self.exit_stage()

    def on_clients_connected(self, pipes):
        self.pipes += pipes

    def on_exit_stage(self):
        print("Clients connected.  Game starting.")
        self.successor = MultiplayerServerGameStage(
                self.world, self.referee, self.ai_actors, self.pipes)


class PostgameSplashStage (Stage):
    """
    Display a "Game Over" message and exit once the player hits <Enter>.
    """

    def on_enter_stage(self):
        print("Game over.")
        self.exit_stage()


class MultiplayerDebugger:
    """
    Simultaneously plays any number of different game theaters, executing each 
    theater in its own process.  This greatly facilitates the debugging and 
    testing multiplayer games.
    """
    names = [
            "Alice",
            "Bob",
            "Carol",
            "Dave",
            "Eve",
            "Fred",
    ]

    class Logger:

        def __init__(self, name, use_file=False):
            self.name = name.lower()
            self.header = '%6s: ' % name
            self.path = '%s.log' % self.name
            self.use_file = use_file
            self.last_char = '\n'

        def __enter__(self):
            import sys
            sys.stdout, self.stdout = self, sys.stdout
            if self.use_file: self.file = open(self.path, 'w')

        def __exit__(self, *ignored_args):
            import sys
            sys.stdout = self.stdout
            if self.use_file: self.file.close()

        def write(self, line):
            annotated_line = ''

            if self.last_char == '\n':
                annotated_line += self.header

            annotated_line += line[:-1].replace('\n', '\n' + self.header)
            annotated_line += line[-1]

            self.last_char = line[-1]

            self.stdout.write(annotated_line)
            if self.use_file: self.file.write(line)

        def flush(self):
            pass


    def __init__(self, world_cls, referee_cls, gui_actor_cls, num_guis=2, 
            ai_actor_cls=None, num_ais=0, host=default_host, port=default_port, 
            theater_cls=PygletTheater):

        self.theater_cls = theater_cls
        self.world_cls = world_cls
        self.referee_cls = referee_cls
        self.gui_actor_cls = gui_actor_cls
        self.num_guis = num_guis
        self.ai_actor_cls = ai_actor_cls
        self.num_ais = num_ais
        self.host = host
        self.port = port

    def play(self, executor=None):
        if not executor:
            from concurrent.futures import ProcessPoolExecutor
            executor = ProcessPoolExecutor()

        with executor:
            executor.submit(self.play_server)
            for i in range(self.num_guis):
                executor.submit(self.play_client, i)

    def play_server(self):
        # Defer instantiation of all the game objects until we're inside our 
        # own subprocess, to avoid having to pickle and unpickle things that 
        # should be pickled.

        info("starting up server")
        theater = self.theater_cls()
        raise ZeroDivisionError
        theater.initial_stage = ServerConnectionStage(
                world=self.world_cls(),
                referee=self.referee_cls(),
                num_clients=self.num_guis,
                ai_actors=[ai_actor_cls() for i in range(self.num_ais)],
                host=self.host,
                port=self.port,
        )
        theater.play()
        info("shutting down server")

    def play_client(self, i):
        # Choose a human name for the client from a list.  If there are more 
        # players than names, complain and ask the user to add more names.

        try: name = self.names[i]
        except IndexError: name = "Client #{}".format(i+1)

        # Defer instantiation of all the game objects until we're inside our 
        # own subprocess, to avoid having to pickle and unpickle things that 
        # should be pickled.
        
        info("starting up client")
        theater = self.theater_cls()
        raise ZeroDivisionError
        theater.initial_stage = ClientConnectionStage(
                world=self.world_cls(),
                gui_actor=self.gui_actor_cls(),
                host=self.host,
                port=self.port,
        )
        theater.play()
        info("shutting down client")


# args: queue

def setup_worker():
    pass
    # try/catch exceptions, pass into queue.
    # add "name" to all loggers.

# args: queue, optional logging handler?

# supervisor:
# setup: configure the logger
# update: flush the logger queue
# shutdown: re-raise exceptions
#
# Might want to write this as a context manager.
#
# How does the logging code use the same queue for multithreading and 
# multiprocessing?

def run_supervisor():
    pass
    # Display logging output
    # re-raise exceptions from workers.


def main(world_cls, referee_cls, gui_actor_cls, ai_actor_cls,
        default_host=default_host, default_port=default_port, argv=None):
    """
Run a game being developed with the kxg game engine.

Usage:
    {sys.argv[0]} sandbox [-v...]
    {sys.argv[0]} client [--host HOST] [--port PORT] [-v...]
    {sys.argv[0]} server <num_guis> [<num_ais>] [options] [-v...] 
    {sys.argv[0]} debug <num_guis> [<num_ais>] [options] [-v...]

Arguments:
    <num_guis>
        The number of human players that will be playing the game.  Only needed 
        by commands that will launch some sort of multiplayer server.

    <num_ais>
        The number of AI players that will be playing the game.  Only needed by 
        commands that will launch some sort of multiplayer server.

Options:
    -x --host HOST          [default: {default_host}]
        The address of the machine running the server.  Must be accessible from 
        the machines running the clients.

    -p --port PORT          [default: {default_port}]
        The port that the server should listen on.  Don't specify a value less 
        than 1024 unless the server is running with root permissions.

    -v --verbose 
        Have the game engine log more information about what it's doing.  You 
        can specify this option several times to get more and more information.

This command is provided so that you can start writing your game with the least 
possible amount of boilerplate code.  However, the clients and servers provided 
by this command are not capable of running a production game.  Once you have 
written your game and want to give it a polished set of menus and options, 
you'll have to write new Stage subclasses encapsulating that logic and you'll 
have to call those stages yourself by interacting more directly with the 
Theater class.  The online documentation has more information on this process.
    """
    import sys, docopt, logging, nonstdlib

    usage = main.__doc__.format(**locals()).strip()
    args = docopt.docopt(usage, argv or sys.argv[1:])
    num_guis = int(args['<num_guis>'] or 1)
    num_ais = int(args['<num_ais>'] or 0)
    host, port = args['--host'], int(args['--port'])
    logging.basicConfig(
            format='%(levelname)s: %(name)s: %(message)s',
            level=nonstdlib.verbosity(args['--verbose']),
    )

    # Use the given game objects and command line arguments to play a game!

    game = PygletTheater()
    ai_actors = [ai_actor_cls() for i in range(num_ais)]

    if args['sandbox']:
        game.initial_stage = UniplayerGameStage(
                world_cls(), referee_cls(), gui_actor_cls(), ai_actors)

    if args['client']:
        game.initial_stage = ClientConnectionStage(
                world_cls(), gui_actor_cls(), host, port)

    if args['server']:
        game.initial_stage = ServerConnectionStage(
                world_cls(), referee_cls(), num_guis, ai_actors, host, port)

    if args['debug']:
        game = MultiplayerDebugger(
                world_cls, referee_cls, gui_actor_cls, num_guis, ai_actor_cls,
                num_ais, host, port)

    game.play()


