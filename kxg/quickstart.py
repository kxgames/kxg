#!/usr/bin/env python3

import linersock
from .errors import *
from .theater import *

default_host = 'localhost'
default_port = 53351

class ClientConnectionStage (Stage):

    def __init__(self, world, gui, host, port):
        super().__init__(self)

        self.world = world
        self.gui = gui
        self.host = host
        self.port = port

        self.on_update_stage = self.on_update_connection
        self.client = linersock.Client(
                host, port, callback=self.on_connection_established)

        self.pipe = None
        self.conversation = None
        self.successor = None

    def on_enter_stage(self):
        print("kxg client running: {}:{}".format(self.host, self.port))

    def on_update_connection(self, time):
        self.client.connect()

    def on_connection_established(self, pipe):
        message = messages.WelcomeClient(self.name)
        self.conversation = linersock.SimpleSend(pipe, message)
        self.conversation.start()

        self.pipe = pipe
        self.on_update_stage = self.on_update_introduction

    def on_update_introduction(self, time):
        self.conversation.update()
        if self.conversation.finished():
            self.exit_stage()

    def on_exit_stage(self):
        game_stage = MultiplayerClientGameStage(self.world, self.gui, self.pipe)
        game_stage.successor = PostgameSplashStage()
        self.successor = game_stage


class ServerConnectionStage (Stage):

    def __init__(self, world, referee, num_players, other_actors=[],
            host=default_host, port=default_port):

        super().__init__(self)
        self.pipes = []
        self.greetings = []
        self.successor = None
        self.world, self.referee = world, referee
        self.host, self.port = host, port
        self.server = linersock.Server(
                host, port, num_players, self.on_clients_connected)

    def on_enter_stage(self):
        print("kxg server running: {}:{}".format(self.host, self.port))
        self.server.open()

    def on_update_stage(self, dt):
        if not self.server.finished():
            self.server.accept()
        else:
            pending_greetings = False
            for greeting in self.greetings:
                finished = greeting.update()
                if not finished: pending_greetings = True

            if not pending_greetings:
                self.exit_stage()

    def on_clients_connected(self, pipes):
        for pipe in pipes:
            greeting = linersock.SimpleReceive(
                    pipe, messages.WelcomeClient)
            greeting.start()

            self.pipes.append(pipe)
            self.greetings.append(greeting)

    def on_exit_stage(self):
        print("Clients connected.  Game starting.")
        pipes = [x.get_pipe() for x in self.greetings]

        self.successor = MultiplayerServerGameStage(
                self.world, self.referee, pipes)


class PostgameSplashStage (Stage):
    """
    Display a "Game Over" message and exit once the player hits <Enter>.
    """

    def __init__(self):
        super().__init__(self)

    def on_enter_stage(self):
        print("Game over.")
        self.exit()


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


    def __init__(self, world, referee, gui_actor, num_players, other_actors=[],
            host=default_host, port=default_port, theater_factory=PygletTheater):

        self.theaters = {}
        self.theaters["Server"] = theater_factory()
        self.theaters["Server"].initial_stage = ServerConnectionStage(
                world, referee, len(gui_actors), other_actors, host, port)

        for i in range(num_players):
            try: name = self.names[i]
            except IndexError: DebuggingTooManyPlayers(self.names)

            self.theaters[name] = theater_factory()
            self.theaters[name].initial_stage = ClientConnectionStage(
                    deepcopy(world), deepcopy(gui_actor), host, port)

        from concurrent.futures import ProcessPoolExecutor
        self.executor = ProcessPoolExecutor()

    def play(self):
        with self.executor:
            for name in self.theaters:
                self.executor.submit(self.play_theater, name)

    def play_theater(self, name):
        with self.Logger(name):
            self.theaters[name].play()



def main(world, referee, gui_actor, other_actors=[],
        default_host=default_host, default_port=default_port, argv=None):
    """
Run a game being developed with the kxg game engine.

Usage:
    {sys.argv[0]} sandbox
    {sys.argv[0]} client [--host HOST] [--port PORT]
    {sys.argv[0]} server <num_players> [--host HOST] [--port PORT]
    {sys.argv[0]} debug <num_players> [--host HOST] [--port PORT]

Arguments:
    <num_players>
        The number of players that will be playing the game.  Only needed by 
        commands that will launch some sort of multiplayer server.

Options:
    -x --host HOST        [default: {default_host}]
        The address of the machine running the server.  Must be accessible from 
        the machines running the clients.

    -p --port PORT        [default: {default_port}]
        The port that the server should listen on.  Don't specify a value less 
        than 1024 unless the server is running with root permissions.

This command is provided so that you can start writing your game with the least 
possible amount of boilerplate code.  However, the clients and servers provided 
by this command are not capable of running a production game.  Once you have 
written your game and want to give it a polished set of menus and options, 
you'll have to write new Stage subclasses encapsulating that logic and you'll 
have to call those stages yourself by interacting more directly with the 
Theater class.  The online documentation has more information on this process.
    """
    import sys, docopt

    usage = main.__doc__.format(**locals()).strip()
    args = docopt.docopt(usage, argv or sys.argv[1:])
    num_players = int(args['<num_players>'] or 1)
    host, port = args['--host'], int(args['--port'])
    game = PygletTheater()

    if args['sandbox']:
        game.initial_stage = UniplayerGameStage(
                world, referee, [gui_actor] + other_actors)

    if args['client']:
        game.initial_stage = ClientConnectionStage(
                world, gui_actor, host, port)

    if args['server']:
        game.initial_stage = ServerConnectionStage(
                world, referee, num_players, other_actors, host, port)

    if args['debug']:
        game = MultiplayerDebugger(
                world, referee, gui_actor, num_players, other_actors,
                host, port)

    game.play()


