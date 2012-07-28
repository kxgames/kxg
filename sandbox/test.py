#!/usr/bin/env python

import engine

# Setup Tests {{{1

def setup_tests(world):

    world.create_unit()
    world.create_unit()

    world.create_building()
    world.create_building()

# Read-Only Test {{{1

def read_only_test(world):

    with engine.ProtectedLock('gui'):

        units = world.get_units()
        buildings = world.get_buildings()

        print "Frame %d" % read_only_test.counter
        print "========"

        read_only_test.counter += 1

        print ( units[0].get_attack(),
                units[0].get_health(),
                units[0].get_animation() )

        print ( buildings[0].get_production(),
                buildings[0].get_health(),
                buildings[0].get_menu() )

        try:
            units[0].fight(units[1])
            units[1].fight(units[0])

        except engine.PermissionError: pass
        else: raise AssertionError

        print

read_only_test.counter = 1

# Full-Access Test {{{1

def full_access_test(world):

    with engine.UnprotectedLock():

        units = world.get_units()
        buildings = world.get_buildings()

        units[0].fight(units[1])
        units[1].fight(units[0])

        units[0].fight(units[1])
        units[1].fight(buildings[0])

# }}}1

class World (engine.Token):

    # Constructor {{{1

    def __init__(self, map=(500, 500)):
        self.map = map
        self.units = []
        self.buildings = []

    # Getters {{{1

    @engine.data_getter
    def get_map(self):
        return self.map

    @engine.data_getter
    def get_units(self):
        return self.units

    @engine.data_getter
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

class Unit (engine.Token):

    # Constructor {{{1

    def __init__(self, attack, health):
        self.attack = attack
        self.health = health

    def __extend__(self):
        return { 'gui' : UnitInterface }

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

class Building (engine.Token):

    # Constructor {{{1

    def __init__(self, production, health):
        self.production = production
        self.health = health

    def __extend__(self):
        return { 'gui' : BuildingInterface }

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

class UnitInterface (engine.Extension):

    # Extension Data {{{1

    def __init__(self, token):
        self.animation = [ 'frame-1', 'frame-2' ]

    def get_animation(self):
        return self.animation

    # }}}1

class BuildingInterface (engine.Extension):

    # Extension Data {{{1

    def __init__(self, token):
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
