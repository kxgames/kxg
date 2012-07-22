#!/usr/bin/env python

import path
import engine

# Don't use __getattr__ in Token classes.  These attributes will not be
# accessible to proxies.
#
# Don't add getters to the token class after it has been instantiated.  The
# proxies won't find them.

# Only methods can be mde accessible through proxies, not attributes.

# Setup Tests {{{1

def setup_tests(world):

    world.create_unit()
    world.create_unit()

    world.create_building()
    world.create_building()

# Read-Only Test {{{1

def read_only_test(world):

    proxy_world = world.get_proxy('gui')

    proxy_units = proxy_world.get_units()
    proxy_buildings = proxy_world.get_buildings()

    print "Frame %d" % read_only_test.counter
    print "========"

    read_only_test.counter += 1

    print ( proxy_units[0].get_attack(),
            proxy_units[0].get_health(),
            proxy_units[0].get_animation() )

    print ( proxy_buildings[0].get_production(),
            proxy_buildings[0].get_health(),
            proxy_buildings[0].get_menu() )

    try:
        proxy_units[0].fight(proxy_units[1])
        proxy_units[1].fight(proxy_units[0])

    except KeyError: pass
    else: raise AssertionError

    print

read_only_test.counter = 1

# Full-Access Test {{{1

def full_access_test(world):

    units = world.get_units()
    buildings = world.get_buildings()

    units[0].fight(units[1])
    units[1].fight(units[0])

    units[0].fight(units[1])
    units[1].fight(buildings[0])

# }}}1

class World (engine.GameToken):

    # Constructor {{{1

    def __init__(self, map=(500, 500)):
        engine.GameToken.__init__(self)

        self.map = map
        self.units = []
        self.buildings = []

    # Getters {{{1

    @engine.data_getter
    def get_map(self):
        return self.map

    # The token_getter decorator accepts an optional argument which specifies
    # how the tokens returned by this function can be converted to proxies.
    # This will be handled automatically for singletons, lists, tuples, and
    # dictionaries.

    @engine.token_getter
    def get_units(self):
        return self.units

    @engine.token_getter
    def get_buildings(self):
        return self.buildings

    # Setters {{{1

    def create_unit(self, attack=15, health=100):
        unit = Unit(attack, health)
        self.units.append(unit)

    def create_building(self, production=10, health=500):
        building = Building(production, health)
        self.buildings.append(building)

    # }}}1

class Unit (engine.GameToken):

    # Constructor {{{1

    def __init__(self, attack, health):
        engine.GameToken.__init__(self)

        self.attack = attack
        self.health = health

    @classmethod
    def get_proxy_classes(cls):
        return { 'gui' : GuiUnitProxy }

    # Getters {{{1

    @engine.data_getter
    def get_attack(self):
        return self.attack

    @engine.data_getter
    def get_health(self):
        return self.health

    # Setters {{{1

    def fight(self, unit):
        unit.health -= self.attack

    # }}}1

class Building (engine.GameToken):

    # Constructor {{{1

    def __init__(self, production, health):
        engine.GameToken.__init__(self)

        self.production = production
        self.health = health

    @classmethod
    def get_proxy_classes(cls):
        return { 'gui' : GuiBuildingProxy }

    # Getters {{{1

    @engine.data_getter
    def get_production(self):
        return self.production

    @engine.data_getter
    def get_health(self):
        return self.health

    # Setters {{{1

    def develop(self):
        self.production += 2

    # }}}1

class GuiUnitProxy (engine.GameTokenProxy):

    # Proxy Data {{{1

    def __init__(self):
        self.animation = [ 'frame-1', 'frame-2' ]

    def get_animation(self):
        return self.animation

    # }}}1

class GuiBuildingProxy (engine.GameTokenProxy):

    # Proxy Data {{{1

    def __init__(self):
        self.menu = [ 'button-1', 'button-2' ]

    def get_menu(self):
        return self.menu

    # }}}1

if __name__ == '__main__':

    world = World()

    setup_tests(world)
    read_only_test(world)

    full_access_test(world)
    read_only_test(world)
