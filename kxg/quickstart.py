#!/usr/bin/env python3

# Imports (fold)
import linersock
from .errors import *
from .loops import Loop
from .stages import                                                         \
        Stage,                                                              \
        UniplayerGameStage,                                                 \
        MultiplayerClientGameStage,                                         \
        MultiplayerServerGameStage


class UniplayerLoop (Loop):

    def __init__(self, world, referee, *other_actors):
        game_stage = UniplayerGameStage(world, referee, list(other_actors))
        Loop.__init__(self, game_stage)


class MultiplayerClientLoop (Loop):

    def __init__(self, world, gui, host, port):
        stage = ClientConnectionStage(world, gui, host, port)
        super().__init__(self, stage)


class MultiplayerServerLoop (Loop):

    def __init__(self, world, referee, num_players, host, port):
        stage = ServerConnectionStage(world, referee, num_players, host, port)
        super().__init__(self, stage)


class MultiplayerDebugger:
    """
    Simultaneously plays any number of different game loops, executing each 
    loop in its own process.  This greatly facilitates the debugging and 
    testing multiplayer games.
    """

    from multiprocessing import Process

    class KxgThread(Process):

        def __init__(self, name, loop):
            MultiplayerDebugger.Process.__init__(self, name=name)
            self.loop = loop
            self.logger = MultiplayerDebugger.Logger(name)

        def __nonzero__(self):
            return self.is_alive()

        def run(self):
            try:
                with self.logger:
                    self.loop.play(50)
            except KeyboardInterrupt:
                pass

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


    names = [
            "Alice",
            "Bob",
            "Carol",
            "Dave",
            "Eve",
            "Fred",
    ]

    def __init__(self, world, referee, other_actors, host, port):
        if num_players > len(self.names):
            raise DebuggingTooManyPlayers(self.names)

        self.threads = []

        self.threads.append(self.KxgThread("Server",
            MultiplayerServerLoop(world, referee, num_players, host, port)))

        for i in range(num_players):
            self.threads.append(self.KxgThread(names[i],
                MultiplayerClientLoop(world, gui, host, port)))

    def play(self):
        try:
            for thread in self.threads:
                thread.start()

            for thread in self.threads:
                thread.join()

        except KeyboardInterrupt:
            pass



class ClientConnectionStage (Stage):

    def __init__(self, world, gui, host, port):
        super().__init__(self)

        self.world = world
        self.gui = gui
        self.host = host
        self.port = port

        self.update = self.update_connection
        self.client = linersock.Client(
                host, port, callback=self.connection_established)

        self.pipe = None
        self.conversation = None
        self.successor = None

    def setup(self):
        print("Seacow client running: {}:{} ({})".format(
            self.host, self.port, self.name))

        window = self.get_loop().get_window()
        # Show a "Waiting for clients to connect..." message.

    def update_connection(self, time):
        self.client.connect()

    def connection_established(self, pipe):
        message = messages.WelcomeClient(self.name)
        self.conversation = linersock.SimpleSend(pipe, message)
        self.conversation.start()

        self.pipe = pipe
        self.update = self.update_introduction

    def update_introduction(self, time):
        self.conversation.update()
        if self.conversation.finished():
            self.exit_stage()

    def teardown(self):
        pipe = self.pipe

        game_stage = MultiplayerClientGameStage(self.world, self.gui, pipe)
        postgame_stage = PostgameSplashStage()

        self.successor = game_stage
        game_stage.successor = postgame_stage


class ServerConnectionStage (Stage):

    def __init__(self, world, referee, num_players, host, port):
        super().__init__(self)

        self.pipes = []
        self.greetings = []
        self.successor = None
        self.world, self.referee = world, referee
        self.host, self.port = host, port
        self.server = linersock.Server(
                host, port, num_players, self.clients_connected)

    def setup(self):
        print("kxg server running: {}:{}".format(self.host, self.port))
        self.server.open()

    def update(self, time):
        if not self.server.finished():
            self.server.accept()
        else:
            pending_greetings = False
            for greeting in self.greetings:
                finished = greeting.update()
                if not finished: pending_greetings = True

            if not pending_greetings:
                self.exit_stage()

    def clients_connected(self, pipes):
        for pipe in pipes:
            greeting = linersock.SimpleReceive(
                    pipe, messages.WelcomeClient)
            greeting.start()

            self.pipes.append(pipe)
            self.greetings.append(greeting)

    def teardown(self):
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
        pass

    def on_update_stage(self, time):
        pass

    def on_exit_stage(self):
        pass



def main(world, referee, gui, default_host='localhost', default_port=53351):
    import sys, docopt

    args = docopt.docopt("""\
Run a game being developed with the kxg game engine.

Usage:
    {sys.argv[0]} sandbox
    {sys.argv[0]} client [--host] [--port]
    {sys.argv[0]} server <num_players> [--host] [--port]
    {sys.argv[0]} debug <num_players> [--host] [--port]

Arguments:
    <num_players>
        The number of players that will be playing the game.  Only needed by 
        commands that will run some sort of multiplayer server.

Options:
    -x --host [HOST]        [default: {default_host}]
        The address of the machine running the server.  Must be accessible from 
        the machines running the clients.

    -p --port [PORT]        [default: {default_port}]
        The port that the server should listen on.  Don't specify a value less 
        than 1024 unless the server is running with root permissions.

This command is provided so that you can start writing your game with the least 
possible amount of boilerplate code.  However, the clients and servers provided 
by this command are not capable of running a production game.  Once you have 
written your game and want to give it a polished set of menus and options, 
you'll have to write new Stage subclasses encapsulating that logic and you'll 
have to call those stages yourself by interacting more directly with the Loop 
class.  The online documentation describes how to do this in more detail.
""".format(**locals()))

    num_players = int(args['<num_players>'] or 1)
    host, port = args['--host'], int(args['--port'])

    if args['sandbox']:
        game = UniplayerLoop(world, referee, gui)

    if args['client']:
        game = MultiplayerClientLoop(world, gui, host, port)

    if args['server']:
        game = MultiplayerServerLoop(world, referee, num_players, host, port)

    if args['debug']:
        game = MultiplayerDebugger(world, referee, gui, num_players, host, port)

    game.play()
