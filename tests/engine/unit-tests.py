#!/usr/bin/env python

import kxg
import testing
import helpers.pipes

import time
from socket import *

class Loop (kxg.Loop):

    def __init__(self, stage):
        self.stage = stage


class Actor (kxg.Actor):

    def __init__(self, name):
        kxg.Actor.__init__(self)

        self.name = name
        self.player = None
        self.frame = 0
        self.soldiers_pending = False

    def __str__(self):
        return '<Actor name="%s">' % self.name

    def setup(self):
        pass

    def update(self, time):
        self.frame += 1


class Referee (kxg.Referee):

    def __init__(self, num_players):
        kxg.Referee.__init__(self)
        self.num_players = num_players

    def __str__(self):
        return "<Referee>"

    __repr__ = __str__

    def game_started(self):
        return self.world.has_game_started()

    def game_over(self):
        return self.world.has_game_ended()

    def handle_create_player(self, message):
        if len(self.world.players) == self.num_players:
            message = StartGame()
            self.send_message(message)

    def handle_defeat_player(self, message):
        if len(self.world.players) == 1:
            message = FinishGame()
            self.send_message(message)



class World (kxg.World):

    def __init__(self):
        kxg.World.__init__(self)
        self.players = []
        self.game_started = False
        self.game_ended = False

    def update(self, time):
        from itertools import permutations
        for player, opponent in permutations(self.players, 2):
            player.fight(opponent)


    def start_game(self, message):
        self.game_started = True

    def finish_game(self, message):
        self.game_ended = True

    def create_player(self, message):
        self.add_token(message.player, self.players)
        self.add_token(message.player.tower)

    def defeat_player(self, message):
        self.remove_token(message.player, self.players)
        self.remove_token(message.player.tower);

    def create_soldiers(self, message):
        self.add_tokens(message.soldiers, message.player.soldiers)

    def destroy_soldier(self, message):
        soldier = message.soldier
        self.remove_token(soldier, soldier.player.soldiers)

    def message_a(self, message):
        pass

    def message_b(self, message):
        pass

    def message_c(self, message):
        pass


    @kxg.read_only
    def get_players(self):
        return self.players[:]  # Return a shallow copy.

    @kxg.read_only
    def has_game_started (self):
        return self.game_started

    @kxg.read_only
    def has_game_ended (self):
        return self.game_ended


class Player (kxg.Token):

    def __init__(self, name, actor_id):
        kxg.Token.__init__(self)

        self.name = name
        self.actor_id = actor_id
        self.tower = None
        self.soldiers = []

    def __str__(self):
        return '<Player name=%s>' % self.name

    __repr__ = __str__


    @kxg.before_setup
    def before_setup_method(self):
        pass

    @kxg.after_teardown
    def after_teardown_method(self):
        pass


    def fight(self, opponent):
        if self.has_soldiers():
            if opponent.has_soldiers():
                self.attack_soldiers(opponent)
            else:
                self.attack_tower(opponent)
        else:
            if opponent.has_soldiers():
                self.defend_tower(opponent)
            else:
                pass

    def attack_soldiers(self, opponent):
        from itertools import izip, cycle

        health_key = lambda soldier: soldier.health
        opponent_soldiers = cycle(sorted(opponent.soldiers, key=health_key))
        matchup_iterator = izip(self.soldiers, opponent_soldiers)

        for mine, theirs in matchup_iterator:
            mine.fight(theirs)

    def attack_tower(self, opponent):
        for soldier in self.soldiers:
            soldier.fight(opponent.tower)

    def defend_tower(self, opponent):
        for soldier in opponent.soldiers:
            self.tower.fight(soldier)


    @kxg.read_only
    def has_soldiers(self):
        return bool(self.soldiers)


class Tower (kxg.Token):

    def __init__(self, player):
        kxg.Token.__init__(self)
        self.player = player
        self.power, self.toughness = 0, 10
        self.health = self.toughness

    def __str__(self):
        arguments = self.get_id(), self.health, self.toughness
        return '<Tower id=%d health=%d/%d>' % arguments

    __repr__ = __str__

    def fight(self, opponent):
        opponent.health -= self.power

    @kxg.read_only
    def report(self, messenger):
        if self.health <= 0:
            message = DefeatPlayer(self.player)
            messenger.send_message(message)


class Soldier (kxg.Token):

    def __init__(self, player):
        kxg.Token.__init__(self)
        self.player = player
        self.power, self.toughness = 2, 6
        self.health = self.toughness

    def __str__(self):
        arguments = self.get_id(), self.power, self.health, self.toughness
        return '<Soldier id=%d attack=%d health=%d/%d>' % arguments

    __repr__ = __str__

    def fight(self, opponent):
        opponent.health -= self.power

    @kxg.read_only
    def report(self, messenger):
        if self.health <= 0:
            message = DestroySoldier(self)
            messenger.send_message(message)



class StartGame (kxg.Message):

    def __str__(self):
        return '<StartGame>'

    def check(self, world, sender_id):
        return True


class FinishGame (kxg.Message):

    def __str__(self):
        return '<FinishGame>'

    def check(self, world, sender_id):
        return True


class CreatePlayer (kxg.Message):

    def __init__(self, name, actor_id):
        self.player = Player(name, actor_id)
        self.player.tower = Tower(self.player)

    def __str__(self):
        return '<CreatePlayer player=%s>' % self.player.name

    def check(self, world, sender_id):
        return True

    def setup(self, world, id_factory):
        self.player.give_id(id_factory)
        self.player.tower.give_id(id_factory)


class DefeatPlayer (kxg.Message):

    def __init__(self, player):
        self.player = player

    def __str__(self):
        return '<DefeatPlayer player=%s>' % self.player.name

    def check(self, world, sender_id):
        return self.player.tower.health <= 0


class CreateSoldiers (kxg.Message):

    def __init__(self, player, count):
        self.player = player
        self.count = count
        self.soldiers = []
    
    def __str__(self):
        arguments = self.player.name, self.count
        return '<CreateSoldiers player=%s, count=%d>' % arguments
    
    def check(self, world, sender_id):
        return self.player.actor_id == sender_id

    def setup(self, world, id_factory):
        for iteration in range(self.count):
            soldier = Soldier(self.player)
            soldier.give_id(id_factory)
            self.soldiers.append(soldier)


class DestroySoldier (kxg.Message):

    def __init__(self, soldier):
        self.soldier = soldier

    def __str__(self):
        arguments = self.soldier.player.name, self.soldier.get_id()
        return '<DestroySoldier player=%s soldier=%d>' % arguments

    def check(self, world, sender_id):
        return self.soldier.health <= 0



class MessageA (kxg.Message):

    def __str__(self):
        return '<MessageA>'

    def check(self, world, sender_id):
        return True


class MessageB (kxg.Message):

    def __str__(self):
        return '<MessageB>'

    def check(self, world, sender_id):
        return True


class MessageC (kxg.Message):

    def __str__(self):
        return '<MessageC>'

    def check(self, world, sender_id):
        return True



@testing.skip
def token_access_control_test():
    # Set up a world and a couple players, to simulate a game.
    world = World()
    alice, bob = Player('Alice'), Player('Bob')

    id_factory = kxg.engine.IdFactory(world)
    alice.give_id(id_factory)
    bob.give_id(id_factory)

    # Make sure that only token methods labeled with @before_setup can be 
    # called before the token has been added to the game world.  This applies 
    # even if unrestricted token access has been granted.
    
    alice.before_setup_method()
    bob.before_setup_method()

    with testing.expect(AssertionError):
        alice.grow()

    with testing.expect(AssertionError):
        alice.after_teardown_method()

    with kxg.engine.UnrestrictedTokenAccess():
        with testing.expect(AssertionError):
            bob.grow()

    with kxg.engine.UnrestrictedTokenAccess():
        with testing.expect(AssertionError):
            bob.after_teardown_method()

    # Make sure that read-only token methods can be called at any time.

    assert alice.get_strategy() == 'grow'
    assert bob.get_strategy() == 'grow'

    # Make sure that the world cannot be modified unless it has been setup and 
    # unlocked first.  Normally the world would be setup by the `GameStage'.

    world._status = kxg.Token._registered
    with kxg.engine.UnrestrictedTokenAccess():
        world.setup()
    
    with testing.expect(AssertionError):
        world.add_players(alice, bob)

    with kxg.engine.UnrestrictedTokenAccess():
        world.add_players(alice, bob)

    # Make sure that read-only token methods can be called at any time.

    assert alice.get_strategy() == 'grow'
    assert bob.get_strategy() == 'grow'

    # Make sure that any normal token method can be called one the tokens have 
    # been setup and unrestricted access has been granted.  If access has not 
    # been granted, make sure that only read-only method can be called.

    with testing.expect(AssertionError):
        alice.attack()

    with testing.expect(AssertionError):
        bob.defend()

    with kxg.engine.UnrestrictedTokenAccess():
        alice.attack()
        bob.defend()

    # Make sure that read-only token methods can be called at any time.

    assert alice.get_strategy() == 'attack'
    assert bob.get_strategy() == 'defend'

    # Make sure that the world must be unlocked in order for players to be 
    # removed, just like it must be locked in order for players to be added.

    with testing.expect(AssertionError):
        world.remove_players(alice, bob)

    with kxg.engine.UnrestrictedTokenAccess():
        world.remove_players(alice, bob)
    
    # Once the tokens have been removed from the world, only methods decorated 
    # with @after_teardown may be called.  This should be true regardless of 
    # whether or not the tokens are locked.

    alice.after_teardown_method()
    bob.after_teardown_method()

    with testing.expect(AssertionError):
        alice.grow()

    with testing.expect(AssertionError):
        alice.before_setup_method()

    with kxg.engine.UnrestrictedTokenAccess():
        with testing.expect(AssertionError):
            bob.grow()

    with kxg.engine.UnrestrictedTokenAccess():
        with testing.expect(AssertionError):
            bob.before_setup_method()

@testing.skip
def token_networking_test():
    hosts, clients = helpers.pipes.connect(2)

    #alice_world = World()
    #alice_actor = Actor("Alice")
    #alice_stage = kxg.MultiplayerClientGameStage(
    #        alice_world, alice_actor, clients[0])

    #bob_world = World()
    #bob_actor = Actor("Bob")
    #bob_stage = kxg.MultiplayerClientGameStage(
    #        bob_world, bob_actor, clients[1])

    #server_world = World()
    #server_actor = Referee(2)
    #server_stage = kxg.MultiplayerServerGameStage(
    #        server_world, server_actor, hosts)

    # The line below triggers the bug just like the two lines above do.
    message = kxg.IdMessage(1)
    hosts[0].send(message)
    hosts[0].deliver()
    #hosts[1].deliver()

    # Assign IDs.
    server_stage.setup()
    #server_stage.update(1)

    # Receive IDs.
    #alice_stage.update(1)
    #bob_stage.update(1)

    #assert alice_stage.is_finished()
    #assert bob_stage.is_finished()

    #alice_stage = alice_stage.get_successor()
    #bob_stage = bob_stage.get_successor()

    ######################################

    # Send a message.
    #alice_stage.setup()
    #bob_stage.setup()

    #alice_actor.send_message(MessageA())
    #alice_actor.send_message(MessageB())
    
    #message = CreatePlayer("Alice", 1)
    #alice_actor.send_message(message)

    #message = CreatePlayer("Bob", 2)
    #bob_actor.send_message(message)

    #alice_stage.update(1)
    #bob_stage.update(1)
    #server_stage.update(1)

    #server_stage.update(1)
    #alice_stage.update(1)
    #bob_stage.update(1)

    clients[0].send('Hello')
    clients[0].send('World')
    clients[0].deliver()

    print "hosts[0].receive():", hosts[0].receive()
    print "hosts[1].receive():", hosts[1].receive()
    print

    hosts[0].send('Fuck')
    hosts[0].send('Off')
    hosts[0].send('Bitches')
    hosts[0].deliver()

    hosts[1].send('Fuck')
    hosts[1].send('Off')
    hosts[1].send('Bitches')
    hosts[1].deliver()

    print "clients[0].receive():", clients[0].receive()
    print "clients[1].receive():", clients[1].receive()

    assert server_world.players[0].name == 'Alice'
    assert alice_world.players[0].name == 'Alice'
    assert bob_world.players[0].name == 'Alice'

    #assert server_world.players[1].name == 'Bob'
    #assert alice_world.players[1].name == 'Bob'
    #assert bob_world.players[1].name == 'Bob'

    assert False

@testing.test
def weird_networking_bug():
    from kxg.network import Server, Client

    prehost = Server('localhost', 53351, 1)
    preclient = Client('localhost', 53351)

    prehost.open()
    while not preclient.finished():
        preclient.connect()
    prehost.accept()

    host = prehost.get_pipes()[0]
    client = preclient.get_pipe()

    host.lock()
    client.lock()

    #xx = client.socket
    #yy = host.socket

    message = 'Identify'
    host.send(message)
    host.deliver()

    print "client.receive():", client.receive()
    print

    client.send('Request')
    client.deliver()

    print "host.receive():", host.receive()
    print

    #print yy.send('Fuck')
    #print xx.recv(4096)
    #print yy.send('You')
    #print xx.recv(4096)

    host.send('Broadcast...')
    host.send('...Response')
    host.deliver()

    print "client.receive():", client.receive()

def foo_bar():
    address = 'localhost', 53351

    def try_to_recv(receiver):
        import socket, errno
        try: return receiver.recv(4096)
        except socket.error, message:
            if message.errno == errno.EAGAIN: return None
            else: raise

    # host.__init__()
    prehost = socket()
    prehost.setblocking(False)
    prehost.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    # client.__init__()
    client = socket()
    client.setblocking(False)

    # host.open()
    prehost.bind(address)
    prehost.listen(5)

    # client.connect()
    while True:
        error = client.connect_ex(address)
        if not error: break

    # host.accept()
    host, address = prehost.accept()

    # host.send()
    host.send('Host to Client: 1')
    print 'client.recv():', try_to_recv(client)

    # client.send()
    client.send('Client to Host: 2')
    print 'host.recv():  ', try_to_recv(host)

    # host.send()
    host.send('Host to Client: 3')
    print 'client.recv():', try_to_recv(client)

    host.send('Host to Client: 4')
    print 'client.recv():', try_to_recv(client); time.sleep(1)
    print 'client.recv():', try_to_recv(client); time.sleep(1)
    print 'client.recv():', try_to_recv(client); time.sleep(1)
    print 'client.recv():', try_to_recv(client); time.sleep(1)
    
#testing.title('Testing the game engine...')
#testing.run()

#weird_networking_bug()
foo_bar()



