#!/usr/bin/env python

import path
import engine
import pickle

# Don't use __getattr__ in Token classes.  These attributes will not be
# accessible to proxies.
#
# Don't add getters to the token class after it has been instantiated.  The
# proxies won't find them.

# Only methods can be made accessible through proxies, not attributes.

def setup_tests(world):
    with engine.UnprotectedTokenLock():
        world.create_unit(1)
        world.create_unit(2)

        world.create_building(3)
        world.create_building(4)

def read_only_test(world, actor):

    print "Frame %d" % read_only_test.counter
    print "========"

    read_only_test.counter += 1

    with engine.ProtectedTokenLock(actor):
        units = world.get_units()
        buildings = world.get_buildings()

        pickled_unit = pickle.dumps(units[0], 2)
        pickled_building = pickle.dumps(buildings[0], 2)

        unit = pickle.loads(pickled_unit)
        building = pickle.loads(pickled_building)

        print ( unit.get_attack(),
                unit.get_health(),
                unit.get_animation() )

        print ( building.get_production(),
                building.get_health(),
                building.get_menu() )
        try:
            units[0].fight(units[1])
            units[1].fight(units[0])
        except AssertionError: pass
        else: raise AssertionError

    print

def full_access_test(world):
    with engine.UnprotectedTokenLock():
        units = world.get_units()
        buildings = world.get_buildings()

        units[0].fight(units[1])
        units[1].fight(units[0])

        units[0].fight(units[1])
        units[1].fight(buildings[0])


read_only_test.counter = 1

class World (engine.World):

    def __init__(self, map=(500, 500)):
        engine.World.__init__(self)
        print 

        self.map = map
        self.units = []
        self.buildings = []

    def get_map(self):
        return self.map

    def get_units(self):
        return self.units

    def get_buildings(self):
        return self.buildings

    @engine.check_for_safety
    def create_unit(self, attack=15, health=100):
        unit = Unit(id, attack, health)
        self.units.append(unit)

    @engine.check_for_safety
    def create_building(self, production=10, health=500):
        building = Building(id, production, health)
        self.buildings.append(building)



class Unit (engine.Token):

    def __init__(self, id, attack, health):
        engine.Token.__init__(self, id)

        self.attack = attack
        self.health = health

    def __extend__(self):
        return { 'gui' : GuiUnitExtension }

    def get_attack(self):
        return self.attack

    def get_health(self):
        return self.health

    @engine.check_for_safety
    def fight(self, unit):
        unit.health -= self.attack


class Building (engine.Token):

    def __init__(self, id, production, health):
        engine.Token.__init__(self, id)

        self.production = production
        self.health = health

    def __extend__(self):
        return { 'gui' : GuiBuildingExtension }

    def get_production(self):
        return self.production

    def get_health(self):
        return self.health

    @engine.check_for_safety
    def develop(self):
        self.production += 2



class GuiActor (engine.Actor):
    def get_name(self):
        return 'gui'

class GuiUnitExtension (engine.TokenExtension):

    def __init__(self, token):
        self.animation = [ 'frame-1', 'frame-2' ]

    def get_animation(self):
        return self.animation


class GuiBuildingExtension (engine.TokenExtension):

    def __init__(self, token):
        self.menu = [ 'button-1', 'button-2' ]

    def get_menu(self):
        return self.menu



if __name__ == '__main__':

    world = World()
    actor = GuiActor()

    setup_tests(world)
    read_only_test(world, actor)

    full_access_test(world)
    read_only_test(world, actor)
