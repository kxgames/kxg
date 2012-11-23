#!/usr/bin/env python

from __future__ import division

import path, testing
import math, pygame

from geometry import *

@testing.test
def vector_accessor_methods(helper):
    v = Vector(3, 4)
    w = Vector(3.5, 4.5)
    x = Vector(3, -4)

    str(v)
    repr(v)

    assert v.x == 3
    assert v.y == 4
    assert v.tuple == (3, 4)
    assert v.pygame == (3, 4); assert w.pygame == (3, 4)
    assert v.magnitude == 5.0
    assert v.magnitude_squared == 25
    assert v.normal == Vector(3, 4) / 5.0
    assert v.orthogonal == Vector(-4, 3)
    assert v.orthonormal == Vector(-4, 3) / 5.0
    assert 0.92 < v.radians < 0.93
    assert 53.1 < v.degrees < 53.2
    assert -0.93 < x.radians < -0.92
    assert -53.2 < x.degrees < -53.1
    assert sum([v, x]) == Vector(6, 0)

    a, b = v
    assert a == 3 and b == 4

    v.x = 1;            assert v.x == 1
    v.y = 2;            assert v.y == 2
    v.tuple = 3, 4;     assert v.x == 3 and v.y == 4
    v.magnitude = 1
    v.radians = 0;      assert 0.99 < v.x < 1.01 and -0.01 < v.y < 0.01
    v.degrees = 90;     assert -0.01 < v.x < 0.01 and 0.99 < v.y < 1.01
    v.set_x(7);         assert v.get_x() == 7
    v.set_y(8);         assert v.get_y() == 8

@testing.test
def vector_overloaded_operators(helper):
    r = Vector(4, 6)
    s = Vector(2, 2)
    t = (2, 2); k = 2

    class MyVector: pass


    u = MyVector()
    u.x = 2
    u.y = 2

    # Hard-coded operators

    assert r[0] == 4
    assert r[1] == 6
    assert -r == Vector(-4, -6)
    assert abs(r) == Vector(4, 6)
    assert bool(r)

    # Equality operators

    assert r == r
    assert r == (4, 6)
    assert (4, 6) == r

    assert r != s
    assert r != t
    assert r != u
    assert s != r
    assert t != r
    assert u != r

    try: r == 2
    except VectorCastError: pass
    else: raise AssertionError

    try: r != 2
    except VectorCastError: pass
    else: raise AssertionError

    # Addition operator
    
    assert r + s == Vector(6, 8)
    assert r + t == Vector(6, 8)
    assert r + u == Vector(6, 8)
    assert s + r == Vector(6, 8)
    assert t + r == Vector(6, 8)
    assert u + r == Vector(6, 8)

    try: r + k
    except VectorCastError: pass
    else: raise AssertionError

    try: k + r
    except VectorCastError: pass
    else: raise AssertionError

    # Subtraction operator
    
    assert r - s == Vector(2, 4)
    assert r - t == Vector(2, 4)
    assert r - u == Vector(2, 4)
    assert s - r == Vector(-2, -4)
    assert t - r == Vector(-2, -4)
    assert u - r == Vector(-2, -4)

    try: r - k
    except VectorCastError: pass
    else: raise AssertionError

    try: k - r
    except VectorCastError: pass
    else: raise AssertionError

    # Multiplication operator
    
    assert r * s == Vector(8, 12)
    assert r * t == Vector(8, 12)
    assert r * k == Vector(8, 12)
    assert s * r == Vector(8, 12)
    assert t * r == Vector(8, 12)
    assert k * r == Vector(8, 12)

    # Division operators
    
    assert r / s == Vector(2, 3)
    assert r / t == Vector(2, 3)
    assert r / k == Vector(2, 3)
    assert s / r == Vector(1/2, 1/3)
    assert t / r == Vector(1/2, 1/3)
    assert k / r == Vector(1/2, 1/3)

    assert r // s == Vector(2, 3)
    assert r // t == Vector(2, 3)
    assert r // k == Vector(2, 3)
    assert s // r == Vector(0, 0)
    assert t // r == Vector(0, 0)
    assert k // r == Vector(0, 0)

    assert r % s == Vector(0, 0)
    assert r % t == Vector(0, 0)
    assert r % k == Vector(0, 0)
    assert s % r == Vector(2, 2)
    assert t % r == Vector(2, 2)
    assert k % r == Vector(2, 2)

    # Exponent operator

    assert r ** s == Vector(16, 36)
    assert r ** t == Vector(16, 36)
    assert r ** k == Vector(16, 36)
    assert s ** r == Vector(16, 64)
    assert t ** r == Vector(16, 64)
    assert k ** r == Vector(16, 64)

    # In-place operators

    r = Vector(4, 6)

    r += s;     assert r == Vector(6, 8)
    r -= s;     assert r == Vector(4, 6)
    r *= s;     assert r == Vector(8, 12)
    r /= s;     assert r == Vector(4, 6)
    r //= s;    assert r == Vector(2, 3)
    r %= s;     assert r == Vector(0, 1)
    r **= s;    assert r == Vector(0, 1)

    r = Vector(4, 6)

    r += t;     assert r == Vector(6, 8)
    r -= t;     assert r == Vector(4, 6)
    r *= t;     assert r == Vector(8, 12)
    r /= t;     assert r == Vector(4, 6)
    r //= t;    assert r == Vector(2, 3)
    r %= t;     assert r == Vector(0, 1)
    r **= t;    assert r == Vector(0, 1)

    r = Vector(4, 6)

    r += u;     assert r == Vector(6, 8)
    r -= u;     assert r == Vector(4, 6)
    r *= u;     assert r == Vector(8, 12)
    r /= u;     assert r == Vector(4, 6)
    r //= u;    assert r == Vector(2, 3)
    r %= u;     assert r == Vector(0, 1)
    r **= u;    assert r == Vector(0, 1)

    r = Vector(4, 6)

    r *= k;     assert r == Vector(8, 12)
    r /= k;     assert r == Vector(4, 6)
    r //= k;    assert r == Vector(2, 3)
    r %= k;     assert r == Vector(0, 1)
    r **= k;    assert r == Vector(0, 1)

    try: r += k
    except VectorCastError: pass
    else: raise AssertionError

    try: r -= k
    except VectorCastError: pass
    else: raise AssertionError

    r = Vector(4, 6)

    r += 0;     assert r == Vector(4, 6)
    r -= 0;     assert r == Vector(4, 6)
    r *= 0;     assert r == Vector(0, 0)
    r **= 0;    assert r == Vector(1, 1)

    try: r / 0
    except: ZeroDivisionError
    else: raise AssertionError

    try: r // 0
    except: ZeroDivisionError
    else: raise AssertionError

    try: r % 0
    except: ZeroDivisionError
    else: raise AssertionError

@testing.test
def vector_math_methods(helper):

    r = Vector(4, 5)
    s = Vector(1, 1)
    t = (1, 1)

    assert r.get_distance(s) == 5
    assert r.get_distance(t) == 5
    assert r.get_manhattan(s) == 7
    assert r.get_manhattan(t) == 7

    r = Vector(3, 4)
    r.normalize()

    assert r == Vector(3, 4) / 5.0

    try: Vector.null().normalize()
    except NullVectorError: pass

    q = Vector(1, 2)
    r = Vector(1, 2)
    s = Vector(1, 4)
    t = (1, 4)

    assert q.get_interpolated(s, 0.5) == Vector(1, 3)
    assert q.get_interpolated(t, 0.5) == Vector(1, 3)

    q.interpolate(s, 0.5)
    r.interpolate(t, 0.5)

    assert q == Vector(1, 3)
    assert r == Vector(1, 3)

    r = Vector(3, 4)
    s = Vector(2, 3)

    assert r.dot_product(s) == r.dot(s) == 18
    assert r.perp_product(s) == r.perp(s) == 1

    r = Vector(2, 2)
    s = Vector(1, 0)
    t = (1, 0)

    x, y = r.get_components(s)
    u, w = r.get_components(t)

    assert x == Vector(0, 2) and y == Vector(2, 0)
    assert u == Vector(0, 2) and w == Vector(2, 0)

    r = Vector(1, 0)
    s = Vector(0, 1)
    z = Vector.null()

    assert r.get_degrees_to(r) == 0
    assert r.get_radians_to(r) == 0
    assert r.get_degrees_to(s) == 90
    assert s.get_degrees_to(r) == -90
    assert r.get_radians_to(s) == math.pi / 2
    assert s.get_radians_to(r) == -math.pi / 2

    try: r.get_radians_to(z)
    except: ZeroDivisionError
    else: raise AssertionError
    
@testing.test
def vector_factory_methods(helper):
    assert Vector.null() == Vector(0, 0)
    assert Vector.from_tuple((3, 4)) == Vector(3, 4)
    assert Vector.from_scalar(2) == Vector(2, 2)

    # Angle-based factories

    degrees = [0, 90, 180, 270]
    radians = [0, math.pi / 2, math.pi, 3 * math.pi / 2]
    vectors = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    for d, r, v in zip(degrees, radians, vectors):
        assert Vector.from_radians(r) == v
        assert Vector.from_degrees(d) == v

    # Randomized factories

    n = 1000
    tolerance = 3 * math.sqrt(n)
    box = Rectangle.from_center((0, 0), 1, 1)

    circle_vectors = [Vector.random() for x in range(n)]
    rectangle_vectors = [Vector.from_rectangle(box) for x in range(n)]
    circle_deviation = sum(circle_vectors).magnitude
    rectangle_deviation = sum(rectangle_vectors).magnitude

    if (circle_deviation > tolerance) or (rectangle_deviation > tolerance):
        print "The random vector factory test are not deterministic, and will "
        print "spuriously fail roughly 0.01% of the time.  This could be the "
        print "cause of the current failure, especially if the factory code "
        print "has not been changed recently.  Try running the test again."

    assert circle_deviation < tolerance
    assert rectangle_deviation < tolerance


@testing.test
def rectangle_accessor_methods(helper):
    r = Rectangle(2, 4, 6, 8)
    s = Rectangle(1, 6, 8, 4)

    str(r)
    repr(r)

    assert r == r
    assert r == r.copy()

    assert r.left == 2
    assert r.center_x == 5
    assert r.right == 8
    assert r.top == 4
    assert r.center_y == 8
    assert r.bottom == 12
    assert r.width == 6
    assert r.height == 8
    assert r.size == (6, 8)

    assert r.top_left == Vector(2, 4)
    assert r.top_center == Vector(5, 4)
    assert r.top_right == Vector(8, 4)
    assert r.center_left == Vector(2, 8)
    assert r.center == Vector(5, 8)
    assert r.center_right == Vector(8, 8)
    assert r.bottom_left == Vector(2, 12)
    assert r.bottom_center == Vector(5, 12)
    assert r.bottom_right == Vector(8, 12)

    assert r.dimensions == ((2, 4), (6, 8))
    assert r.tuple == (2, 4, 6, 8)
    assert r.pygame == pygame.Rect(2, 4, 6, 8)

    assert r.get_grown(1) == Rectangle(1, 3, 8, 10)
    assert r.get_shrunk(1) == Rectangle(3, 5, 4, 6)
    assert r.get_union(s) == Rectangle(1, 4, 8, 8)
    assert r.get_intersection(s) == Rectangle(2, 6, 6, 4)

@testing.test
def rectangle_mutator_methods(helper):
    r = Rectangle(2, 2, 4, 4)
    q = Rectangle(1, 1, 6, 8)
    v = Vector(5, 6)

    assert r + v == Rectangle(7, 8, 4, 4)
    assert r - v == Rectangle(-3, -4, 4, 4)

    r += v;                     assert r == Rectangle(7, 8, 4, 4)
    r -= v;                     assert r == Rectangle(2, 2, 4, 4)

    r.grow(1);                  assert r == Rectangle(1, 1, 6, 6)
    r.shrink(1);                assert r == Rectangle(2, 2, 4, 4)

    r.align_left(q);            assert r == Rectangle(1, 2, 4, 4)
    r.align_center_x(q);        assert r == Rectangle(2, 2, 4, 4)
    r.align_right(q);           assert r == Rectangle(3, 2, 4, 4)
    r.align_top(q);             assert r == Rectangle(3, 1, 4, 4)
    r.align_center_y(q);        assert r == Rectangle(3, 3, 4, 4)
    r.align_bottom(q);          assert r == Rectangle(3, 5, 4, 4)

    r.set_width(6);             assert r == Rectangle(3, 5, 6, 4)
    r.set_height(7);            assert r == Rectangle(3, 5, 6, 7)
    r.set_size(4, 4);           assert r == Rectangle(3, 5, 4, 4)

    r.set_top_left(v);          assert r == Rectangle(5, 6, 4, 4)
    r.set_top_center(v);        assert r == Rectangle(3, 6, 4, 4)
    r.set_top_right(v);         assert r == Rectangle(1, 6, 4, 4)
    r.set_center_left(v);       assert r == Rectangle(5, 4, 4, 4)
    r.set_center(v);            assert r == Rectangle(3, 4, 4, 4)
    r.set_center_right(v);      assert r == Rectangle(1, 4, 4, 4)
    r.set_bottom_left(v);       assert r == Rectangle(5, 2, 4, 4)
    r.set_bottom_center(v);     assert r == Rectangle(3, 2, 4, 4)
    r.set_bottom_right(v);      assert r == Rectangle(1, 2, 4, 4)

    try: r.set_top_left(0)
    except VectorCastError: pass
    else: raise AssertionError

@testing.test
def rectangle_collision_methods(helper):
        box = Rectangle(5, 5, 10, 10)

        class MyShape: pass
        shape = MyShape()

        pairs = [(x, y) for x in range(5)
                        for y in range(5)]

        box_contains = [
                [False, False, False, False, False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, False, False, False, False] ]

        minibox_inside = [
                [False, False, False, False, False],
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, False, False, False, False],
                [False, False, False, False, False] ]

        minibox_touching = [
                [False, False, False, False, False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, False, False, False, False] ]

        for x, y in pairs:
            point = 5 * Vector(x, y)
            minibox = Rectangle.from_center(point, 4, 4)

            shape.top, shape.left = minibox.top_left
            shape.width, shape.height = minibox.size

            assert (point in box) == box_contains[y][x]
            assert box.contains(point) == box_contains[y][x]
            assert box.touching(point) == box_contains[y][x]

            assert (minibox in box) == minibox_inside[y][x]
            assert box.contains(minibox) == minibox_inside[y][x]
            assert box.touching(minibox) == minibox_touching[y][x]

            assert (shape in box) == minibox_inside[y][x]
            assert box.contains(shape) == minibox_inside[y][x]
            assert box.touching(shape) == minibox_touching[y][x]

            assert minibox.touching(box) == minibox_touching[y][x]
            assert minibox.inside(box) == minibox_inside[y][x]
            assert minibox.outside(box) == (not minibox_touching[y][x])

        try: box.inside(0)
        except RectangleCastError: pass
        else: raise AssertionError

        try: box.outside(0)
        except RectangleCastError: pass
        else: raise AssertionError

        try: box.touching(0)
        except RectangleCastError: pass
        else: raise AssertionError

        try: box.contains(0)
        except RectangleCastError: pass
        else: raise AssertionError

@testing.test
def rectangle_factory_methods(helper):

    v = Vector(5, 6)
    t = 7, 8

    assert Rectangle.from_size(1, 2) == Rectangle(0, 0, 1, 2)
    assert Rectangle.from_width(3, ratio=2) == Rectangle(0, 0, 3, 6)
    assert Rectangle.from_height(4, ratio=2) == Rectangle(0, 0, 8, 4)
    assert Rectangle.from_vector(v) == Rectangle(5, 6, 0, 0)
    assert Rectangle.from_vector(t) == Rectangle(7, 8, 0, 0)
    assert Rectangle.from_square(9) == Rectangle(0, 0, 9, 9)
    assert Rectangle.from_dimensions(1, 2, 3, 4) == Rectangle(1, 2, 3, 4)
    assert Rectangle.from_sides(5, 6, 8, 7) == Rectangle(5, 6, 3, 1)
    assert Rectangle.from_top_left(v, 1, 2) == Rectangle(5, 6, 1, 2)
    assert Rectangle.from_top_left(t, 3, 4) == Rectangle(7, 8, 3, 4)
    assert Rectangle.from_center(v, 8, 6) == Rectangle(1, 3, 8, 6)
    assert Rectangle.from_center(t, 4, 2) == Rectangle(5, 7, 4, 2)

    import pygame
    surface = pygame.Surface((600, 400))

    assert Rectangle.from_surface(surface) == Rectangle(0, 0, 600, 400)

    a = Rectangle(1, 1, 4, 4)
    b = Rectangle(4, 4, 4, 4)

    assert Rectangle.from_union(a, b) == Rectangle(1, 1, 7, 7)
    assert Rectangle.from_intersection(a, b) == Rectangle(4, 4, 1, 1)


@testing.test
def shape_interface(helper):
    class MyShape (Shape): pass
    shape = MyShape()

    try: shape.top
    except: NotImplementedError
    else: pass

    try: shape.left
    except: NotImplementedError
    else: pass

    try: shape.width
    except: NotImplementedError
    else: pass

    try: shape.height
    except: NotImplementedError
    else: pass

@testing.test
def shape_pickling(helper):
    import pickle

    original_vector = Vector(3, 4)
    original_rect = Rectangle(2, 4, 6, 8)

    serialized_vector = pickle.dumps(original_vector)
    serialized_rect = pickle.dumps(original_rect)

    pickled_vector = pickle.loads(serialized_vector)
    pickled_rect = pickle.loads(serialized_rect)

    assert original_vector == pickled_vector
    assert original_rect == pickled_rect


testing.title("Testing the geometry module...")
testing.run()
