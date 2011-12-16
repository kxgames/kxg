#!/usr/bin/env python

import path

from sprites import *
from helpers.interface import *

# Slow Movement {{{1
def test_slow_movement():
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
def test_fast_movement():
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

if __name__ == '__main__':

    with TestInterface("Testing the sprite module...", 2) as status:
        status.update();        test_slow_movement()
        status.update();        test_fast_movement()

    TestInterface.report_success()
