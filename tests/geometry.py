#!/usr/bin/env python

import path, testing
from geometry import *

@testing.test
def test_vector_factory_methods(helper):
    assert Vector.null() == Vector(0, 0)

    degrees = (0, 90, 180, 270)
    radians = (0, math.pi / 2, math.pi, 3 * math.pi / 2)

    for d, r in zip(degrees, radians):
        assert Vector.from_radians(r) == Vector.from_degrees(d)

@testing.test
def test_vector_math_methods(helper):
    pass

testing.title("Testing the geometry module...")
testing.run()
