#!/usr/bin/env python

import kxg
import testing
import helpers.pipes

class Loop (kxg.Loop):

    def __init__(self, stage):
        self.stage = stage
        self.finished = False

    def update(self, dt):
        if not self.finished:
            import time; time.sleep(dt)
            kxg.Loop.update(self, dt)

    def exit(self):
        self.finished = True


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
        message = CreatePlayer(self.name, self.id)
        self.send_message(message)

    def update(self, time):
        self.frame += 1


    def handle_create_player(self, message):
        if message.was_sent_from_here():
            self.player = message.player

    def handle_create_soldiers(self, message):
        arguments = message.player.name, message.count
        print '  %s created %d soldiers.' % arguments

    def handle_destroy_soldier(self, message):
        player = message.soldier.player
        arguments = player.name, len(player.soldiers)
        print '  %s has %d soldiers left.' % arguments

    def request_create_soldier(self):
        self.request_create_soldiers(1)

    def request_create_soldiers(self, count):
        message = CreateSoldiers(self.player, count)
        self.send_message(message)
        self.soldiers_pending = True

    def accept_create_soldiers(self, message, confirmed):
        if confirmed:
            self.soldiers_pending = False


class AliceActor (Actor):

    def __init__(self):
        Actor.__init__(self, "Alice")

    def handle_destroy_soldier(self, message):
        Actor.handle_destroy_soldier(self, message)
        if message.soldier.player == self.player:
            self.request_create_soldier()


class BobActor (Actor):

    def __init__(self):
        Actor.__init__(self, "Bob")

    def update(self, time):
        Actor.update(self, time)


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
        print "  %s has been defeated. Tower health: %d" % (
                message.player.name, message.player.tower.health)
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
        if format == "full":
            arguments = self.get_id(), self.health, self.toughness
            return '<Tower id=%d health=%d/%d>' % arguments
        if format == "simple":
            return '(%d/%d)' % (self.health, self.toughness)

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
        if format == "full":
            arguments = self.get_id(), self.power, self.health, self.toughness
            return '<Soldier id=%d attack=%d health=%d/%d>' % arguments
        if format == "simple":
            return '(%d/%d)' % (self.health, self.toughness)

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



@testing.test
def single_player_integration_test():
    world = World()
    referee = Referee(2)
    actors = alice, bob = AliceActor(), BobActor()
    stage = kxg.SinglePlayerGameStage(world, referee, actors)

    integration_test([world], [stage], alice, bob, referee)

@testing.test
def multiplayer_integration_test():
    worlds = World(), World(), World()
    clients, servers = helpers.pipes.connect(2)
    players = alice, bob = AliceActor(), BobActor()
    referee = Referee(2)

    stages = [
            kxg.MultiplayerServerGameStage(worlds[0], referee, servers),
            kxg.MultiplayerClientGameStage(worlds[1], alice, clients[0]),
            kxg.MultiplayerClientGameStage(worlds[2], bob, clients[1]) ]

    integration_test(worlds, stages, alice, bob, referee)

def integration_test(worlds, stages, alice, bob, referee):
    loops = [ Loop(stage) for stage in stages]
    dt = 0.1

    def print_setup_status():
        print 79 * '-'

    def print_pregame_status():
        print 79 * '-'
        print 79 * '='

    def print_game_status():
        global format
        format, old_format = 'simple', format

        print 79 * '-'
        print "Alice Soldiers:", ' '.join(map(str, alice.player.soldiers))
        print "Alice Tower:", alice.player.tower
        print "Bob Soldiers:", ' '.join(map(str, bob.player.soldiers))
        print "Bob Tower:", bob.player.tower

        format = old_format


    # Make sure the game gets setup properly
    for world in worlds:
        assert not world.has_game_started()
        assert not world.has_game_ended()

    for stage in stages:
        stage.setup()

    for each in range(10):
        print_setup_status()
        for loop in loops:
            loop.update(dt)

    assert alice.player is not None
    assert bob.player is not None

    assert len(alice.player.soldiers) == 0
    assert len(bob.player.soldiers) == 0
    assert alice.player.tower.health == 10
    assert bob.player.tower.health == 10

    for world in worlds:
        assert world.has_game_started()
        assert not world.has_game_ended()

    # Make sure the game plays properly
    alice.request_create_soldiers(2)
    bob.request_create_soldiers(3)

    print_pregame_status()

    for each in range(20):
        print_game_status()
        for loop in loops:
            loop.update(dt)

    print_game_status()

    assert len(alice.player.soldiers) == 2
    assert len(bob.player.soldiers) == 0
    assert alice.player.tower.health > 0
    assert bob.player.tower.health < 0

    for world in worlds:
        assert world.has_game_started()
        assert world.has_game_ended()


testing.title('Testing the game engine...')
testing.run()



