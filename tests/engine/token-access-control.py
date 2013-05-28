#!/usr/bin/env python

import kxg
import testing
import helpers.pipes

# This isn't bad, probably enough to merge this branch and to start working on 
# the mailbox id thing.  But I would like to exercise the pickling system a 
# little bit more, which will require tokens that have dependencies on each 
# other.

class World (kxg.World):

    def __init__(self):
        kxg.World.__init__(self)
        self.players = []

    @kxg.read_only
    def get_players(self):
        return self.players[:]  # Return a shallow copy.

    def add_players(self, *players):
        for player in players:
            self.add_token(player, self.players)

    def remove_players(self, *players):
        for player in players:
            self.remove_token(player, self.players)

    @kxg.read_only
    def has_game_started (self):
        return True

    @kxg.read_only
    def has_game_ended (self):
        return False


class Referee (kxg.Referee):

    def get_name(self):
        return 'Test Referee'

class Actor (kxg.Actor):

    def get_name(self):
        return 'Test Actor'


class Player (kxg.Token):

    def __init__(self, name):
        kxg.Token.__init__(self)
        self.name = name
        self.strategy = 'grow'
        self.statistics = None

    def __str__(self):
        return '<Player name=%s>' % self.name

    @kxg.before_setup
    def before_setup_method(self):
        pass

    @kxg.after_teardown
    def after_teardown_method(self):
        pass

    def grow(self):
        self.strategy = 'grow'
    
    def attack(self):
        self.strategy = 'attack'

    def defend(self):
        self.strategy = 'defend'

    @kxg.read_only
    def get_strategy(self):
        return self.strategy



class CreatePlayer (kxg.Message):

    def __init__(self, name):
        self.player = Player(name)

    def check(self, world, sender):
        return True

    def setup(self, world, sender, id_factory):
        self.player.give_id(id_factory)

    def execute(self, world):
        world.add_players(self.player)



@testing.test
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

@testing.test
def token_networking_test():
    hosts, clients = helpers.pipes.connect(2)

    alice_world = World()
    alice_actor = Actor()
    alice_stage = kxg.MultiplayerClientGameStage(
            alice_world, alice_actor, clients[0])

    bob_actor = Actor()
    bob_world = World()
    bob_stage = kxg.MultiplayerClientGameStage(
            bob_world, bob_actor, clients[1])

    server_world = World()
    server_actor = Referee()
    server_stage = kxg.MultiplayerServerGameStage(
            server_world, server_actor, hosts)

    server_stage.setup()
    alice_stage.setup()
    bob_stage.setup()

    message = CreatePlayer('Alice')
    alice_actor.send_message(message)
    alice_stage.update(0)

    server_stage.update(0)
    alice_stage.update(0)
    bob_stage.update(0)

    print server_world, server_world.players
    print alice_world, alice_world.players
    print bob_world, bob_world.players

    assert server_world.players[0].name == 'Alice'
    assert alice_world.players[0].name == 'Alice'
    assert bob_world.players[0].name == 'Alice'



# Networking test
    
testing.title('Testing token access control...')
testing.run()



