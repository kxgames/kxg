#!/usr/bin/env python

import path, testing
from sprites import *

# Slow Movement {{{1
@testing.test
def test_slow_movement(helper):
    sprite = Sprite()

    a, v, r = Vector(1, 0), Vector(2, 0), Vector(0, 0)

    sprite.set_acceleration(a)
    sprite.set_velocity(v)
    sprite.set_position(r)

    sprite.update(2)

    a, v, r = Vector(1, 0), Vector(4, 0), Vector(6, 0)

    assert sprite.get_acceleration() == a
    assert sprite.get_velocity() == v
    assert sprite.get_position() == r

# Fast Movement {{{1
@testing.test
def test_fast_movement(helper):
    sprite = Sprite()

    max_a, max_v = 1, 2
    a, v, r = Vector(10, 0), Vector(20, 0), Vector(0, 0)

    sprite.setup(r, max_a, max_v)

    sprite.set_acceleration(a)
    sprite.set_velocity(v)

    sprite.update(2)

    a, v, r = Vector(1, 0), Vector(2, 0), Vector(4, 0)

    assert sprite.get_acceleration() == a
    assert sprite.get_velocity() == v
    assert sprite.get_position() == r

# }}}1

testing.title("Testing the sprites...")
testing.run()
