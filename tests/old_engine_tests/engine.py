#!/usr/bin/env python

import path
import engine
import testing

class World (engine.World):

    def __init__(self):
        engine.World.__init__(self)
        self.nations = []

    def add_nation(self, nation):
        self.add_token(nation)
        self.nations.append(nation)

    def add_city(self, city):
        self.add_token(city)
        city.nation.cities.append(city)

    def add_army(self, army):
        self.add_token(army)
        army.nation.armies.append(army)


class Nation (engine.Token):

    def __init__(self, name):
        engine.Token.__init__(self)
        self.name = name
        self.cities = []
        self.armies = []


class City (engine.Token):

    def __init__(self, nation, resource):
        engine.Token.__init__(self)
        self.nation = nation
        self.resource = resource


class Army (engine.Token):

    def __init__(self, nation, manpower):
        engine.Token.__init__(self)
        self.nation = nation
        self.manposer = manpower



class CreateNation (engine.Greeting):
    pass

class CreateCity (engine.Message):
    def __init__(self, nation, resource):
        self.city = City(nation, resource)

class CreateArmy (engine.Message):
    pass


class Referee (engine.Referee):
    pass

class Gui (engine.Actor):
    pass


@testing.setup
def setup_world(helper):
    helper.world = World()
    helper.nation = Nation('Bob')
    helper.id = engine.IdFactory(helper.world)

    with engine.UnprotectedTokenLock():
        helper.nation.give_id(helper.id)
        helper.world.add_nation(helper.nation)

@testing.test
def test_token_serialization(helper):

    serializer = engine.TokenSerializer(helper.world)
    deserializer = engine.TokenSerializer(helper.world)

    # Test the serialization of an unregistered token.  This should result in 
    # two cities that both point to the same nation.

    original_city = City(helper.nation, 'food')
    packed_city = serializer.pack(original_city)
    duplicate_city = deserializer.unpack(packed_city)

    assert duplicate_city is not original_city
    assert duplicate_city.nation is original_city.nation
    assert duplicate_city.resource == 'food'

    # Test the serialization of a registered token.  This should not create a 
    # copy of the original city object.

    original_city = City(helper.nation, 'wood')

    with engine.UnprotectedTokenLock():
        original_city.give_id(helper.id)
        helper.world.add_nation(original_city)

    packed_city = serializer.pack(original_city)
    duplicate_city = deserializer.unpack(packed_city)

    assert duplicate_city is original_city
    assert duplicate_city.nation is original_city.nation

    # Test the serialization of a message object.  This should not result in 
    # the nation object being copied.

    original_message = CreateCity(helper.nation, 'ore')
    packed_message = serializer.pack(original_message)
    duplicate_message = deserializer.unpack(packed_message)

    assert duplicate_message.city is not original_message.city
    assert duplicate_message.city.nation is original_message.city.nation
    assert duplicate_message.city.resource == 'ore'


testing.title("Testing the engine module...")
testing.run()

