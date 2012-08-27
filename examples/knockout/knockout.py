#!/usr/bin/env python

# Things to Change
# ================
# 1. It was a little hard to figure out that I need to call
#    conversation.start() before conversation.update().  This is necessary
#    because of how pipes must be locked, but the error is an assertion error
#    from deep within the pipe class.  The conversation should recognize this
#    situation and throw a more helpful error.
#
# 2. I think the pregame part of the program is too complicated.  The code that
#    establishes the connection and communicates the player name is too long
#    and obfuscated.  I should think of way to simplify it.  A way to manage
#    multiple simultaneous conversations would be helpful.

import kxg
import sys, select, string

class ClientLoop (kxg.MainLoop):
    def __init__(self, name, host, port):
        self.stage = ClientConnectionStage(self, name, host, port)

class ServerLoop (kxg.MainLoop):
    def __init__(self, host, port):
        self.stage = ServerConnectionStage(self, host, port)

class SandboxLoop (kxg.MainLoop):
    def __init__(self, name):
        world, referee = World(), Referee()
        actors_to_greetings = {
                Console() : CreateBoxer(name),
                AI() : CreateBoxer('Computer') }

        self.stage = kxg.SinglePlayerGameStage(
                self, world, referee, actors_to_greetings)

class ClientConnectionStage (kxg.Stage):

    def __init__(self, master, name, host, port):
        kxg.Stage.__init__(self, master)

        self.name = name
        self.update = self.update_connection
        self.client = kxg.network.PickleClient(
                host, port, callback=self.client_connected)

        self.pipe = None
        self.conversation = None
        self.successor = None

    def setup(self):
        pass

    def update_connection(self, time):
        self.client.connect()

    def update_introduction(self, time):
        self.conversation.update()

        if self.conversation.finished():
            self.exit_stage()

    def client_connected(self, pipe):
        message = IntroduceClient(self.name)
        self.conversation = kxg.messaging.SimpleSend(pipe, message)
        self.conversation.start()

        self.pipe = pipe
        self.update = self.update_introduction

    def teardown(self):
        world, actor = World(), Console()
        self.successor = kxg.MultiplayerClientGameStage(
                self, world, actor, self.pipe)

    def get_successor(self):
        return self.successor


class ServerConnectionStage (kxg.Stage):

    def __init__(self, master, host, port, players=2):
        kxg.Stage.__init__(self, master)

        self.server = kxg.network.PickleServer(
                host, port, players, self.accept_client)

        self.pipes = []
        self.conversations = []
        self.successor = None

        self.update = self.update_connections

    def setup(self):
        self.server.open()

    def update_connections(self, time):
        self.server.accept()

    def update_introductions(self, time):
        all_finished = True

        for chat in self.conversations:
            finished = chat.update()
            all_finished = (finished and all_finished)

        if all_finished:
            self.exit_stage()

    def accept_client(self, pipes):
        self.pipes.append(pipes)

        for pipe in pipes:
            chat = kxg.messaging.SimpleReceive(pipe, IntroduceClient)
            self.conversations.append(chat)

        for chat in self.conversations:
            chat.start()

        self.update = self.update_introductions

    def teardown(self):
        world, referee = World(), Referee()
        pipes_to_greetings = {}

        for chat in self.conversations:
            pipe = chat.get_pipe()
            name = chat.get_message().name
            pipes_to_greetings[pipe] = CreateBoxer(name)

        self.successor = kxg.MultiplayerServerGameStage(
                self, world, referee, pipes_to_greetings)

    def get_successor(self):
        return self.successor



class IntroduceClient (object):
    def __init__(self, name):
        self.name = name

class CreateBoxer (kxg.Greeting):

    def __init__(self, name):
        self.name = name
        self.boxer = None
        self.id = None

    def get_player(self):
        return self.boxer

    def check(self, world, boxer):
        if world.is_game_ready():
            return False
        if world.has_game_started():
            return False
        return True

    def setup(self, world, id_factory):
        self.id = id_factory.next()

    def execute(self, world):
        self.boxer = world.create_boxer(self.id, self.name)

    def notify(self, actor):
        is_you = self.was_sent_from_here()
        actor.create_boxer(self.boxer, is_you)


class StartGame (kxg.Message):

    def check(self, world, boxer):
        return not world.has_game_started()

    def execute(self, world):
        world.start_game()


class PunchBoxer (kxg.Message):

    def __init__(self, boxer):
        self.puncher = boxer
        self.damage = None

    def check(self, world, boxer):
        return self.puncher is boxer

    def setup(self, world, id_factory):
        time = world.get_elapsed_time()
        damage = self.puncher.get_attack(time)

        self.damage = abs(damage)
        self.backfired = (damage < 0)

    def execute(self, world):
        punchee = self.puncher.get_opponent()
        world.punch_boxer(self.puncher, punchee, self.damage, self.backfired)

    def notify(self, actor):
        punchee = self.puncher.get_opponent()
        actor.punch_boxer(self.puncher, punchee, self.damage, self.backfired)


class FinishGame (kxg.Message):

    def __init__(self, winner):
        self.winner = winner

    def check(self, world, player):
        return player == 'referee'

    def execute(self, world):
        world.finish_game(self.winner)

    def notify(self, actor):
        actor.finish_game(self.winner)



class World (kxg.World):

    def __init__(self):
        kxg.World.__init__(self)

        self.tokens = {}
        self.boxers = []
        self.winner = None

        self.elapsed_time = 0
        self.game_started = False

    def setup(self):
        pass

    def update(self, time):
        if self.game_started and not self.winner:
            self.elapsed_time += time

    def teardown(self):
        pass

    def start_game(self):
        self.game_started = True

        boxers = self.boxers
        boxers[0].set_opponent(boxers[1])
        boxers[1].set_opponent(boxers[0])

    def create_boxer(self, id, name):
        boxer = Boxer(id, name)
        self.tokens[id] = boxer
        self.boxers.append(boxer)
        return boxer

    def punch_boxer(self, puncher, punchee, damage, backfired):
        self.elapsed_time = 0

        if not backfired: punchee.take_damage(damage)
        else:             puncher.take_damage(damage)

    def finish_game(self, winner):
        self.winner = winner


    @kxg.data_getter
    def get_token(self, id):
        return self.tokens[id]

    @kxg.data_getter
    def get_elapsed_time(self):
        return self.elapsed_time

    @kxg.data_getter
    def get_boxers(self):
        return self.boxers

    @kxg.data_getter
    def get_winner(self):
        return self.winner

    @kxg.data_getter
    def is_game_ready(self):
        return len(self.boxers) == 2

    @kxg.data_getter
    def has_game_started(self):
        return self.game_started

    @kxg.data_getter
    def is_game_over(self):
        return self.winner is not None


class Referee (kxg.Referee):

    name = 'referee'

    def __init__(self):
        kxg.Referee.__init__(self)

    def get_name(self):
        return Referee.name

    def setup(self, world):
        self.world = world

    def update(self, time):
        pass

    def teardown(self):
        pass

    def create_boxer(self, boxer, is_you):
        if self.world.is_game_ready():
            message = StartGame()
            self.send_message(message)

    def punch_boxer(self, puncher, punchee, damage, backfired):
        boxer = punchee if not backfired else puncher
        opponent = boxer.get_opponent()

        if boxer.get_health() < 0:
            message = FinishGame(winner=opponent)
            self.send_message(message)


    def finish_game(self, winner):
        self.finish()

    def teardown(self):
        pass


class Console (kxg.Actor):

    name = 'console'

    your_punch_message = "You punched %s for %d damage!"
    their_punch_message = "You were punched by %s for %d damage!"
    your_backfire_message = "Ouch! You punched yourself for %d damage!"
    their_backfire_message = "%s punched himself for %d damage!"

    status_message = '(%d:%02d)    %s: %d    %s: %d'
    victory_message = "You win!"; defeat_message = "You lose."

    def __init__(self, quiet=False):
        kxg.Actor.__init__(self)
        self.quiet = quiet
        self.rows, self.columns = 0, 0
        self.timer = 0

    def get_name(self):
        return Console.name

    def setup(self, world):
        self.world = world

        # Try to accurately determine the size of the terminal.  If that
        # doesn't work for some reason, assume the terminal is 25 by 80.

        try:
            from subprocess import check_output
            rows, columns = check_output('stty size', shell=True).split()
            self.rows, self.columns = int(rows), int(columns) - 1
        except:
            self.rows, self.columns = 25, 80

    def update(self, time):
        if not self.world.has_game_started():
            return

        self.update_input(time)
        self.update_display(time)

    def update_input(self, time):
        available = select.select([sys.stdin], [], [], 0)
        readable = available[0]

        if sys.stdin in readable:
            buffer = raw_input()
            message = PunchBoxer(self.boxer)
            self.send_message(message)

    def update_display(self, time):
        self.timer += time
        if self.timer > 0.5:
            self.timer = 0

            boxer = self.boxer
            opponent = self.boxer.get_opponent()
            elapsed_time = self.world.get_elapsed_time()

            status_message = Console.status_message % (
                    elapsed_time // 60,
                    elapsed_time % 60,
                    boxer.get_name(),
                    boxer.get_health(),
                    opponent.get_name(),
                    opponent.get_health() )

            sys.stdout.write('\r' + status_message)
            sys.stdout.flush()

    def teardown(self):
        pass

    def create_boxer(self, boxer, is_you):
        if is_you: self.boxer = boxer

    def punch_boxer(self, puncher, punchee, damage, backfired):
        punch_data = punchee.get_name(), damage
        backfire_data = puncher.get_name()

        if puncher is self.boxer:
            if not backfired:
                print '\r' + Console.your_punch_message % punch_data
            else:
                print '\r' + Console.your_backfire_message % damage
        else:
            if not backfired:
                print '\r' + Console.their_punch_message % punch_data
            else:
                print '\r' + Console.their_backfire_message % backfire_data

    def finish_game(self, winner):
        if winner is self.boxer:
            print '\r' + Console.victory_message
        else:
            print '\r' + Console.defeat_message

        self.finish()


class AI (kxg.Actor):

    name = 'ai'

    def get_name(self):
        return AI.name

    def setup(self, world):
        pass

    def update(self, time):
        pass

    def teardown(self):
        pass

    def create_boxer(self, boxer, is_you):
        pass

    def punch_boxer(self, puncher, punchee, damage, backfired):
        pass

    def finish_game(self, winner):
        self.finish()


class Boxer (kxg.Token):

    health = 100
    attack = 2, 3, -10       # Polynomial coefficients.

    def __init__(self, id, name):
        kxg.Token.__init__(self, id)
        self.name = name
        self.health = Boxer.health
        self.attack = Boxer.attack

    @kxg.data_getter
    def get_name(self):
        return self.name

    @kxg.data_getter
    def get_opponent(self):
        return self.opponent

    @kxg.data_getter
    def get_health(self):
        return self.health

    @kxg.data_getter
    def get_attack(self, time):
        a, t = self.attack, time
        return int(a[0]*t**2 + a[1]*t + a[2])

    def set_opponent(self, opponent):
        self.opponent = opponent

    def take_damage(self, damage):
        self.health -= damage



