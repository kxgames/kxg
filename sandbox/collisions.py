from __future__ import division

import math, shapes
from vector import Vector

class Collisions:

    # Points and Lines {{{1
    @staticmethod
    def points_nearby(first, second, padding):
        return Vector.get_distance(first, second) <= padding

    @staticmethod
    def point_on_line(point, line):
        if line.degenerate:
            return Collisions.points_nearby(point, line.head, 0)

        u = line.head - line.tail
        v = point - line.tail

        if u == v:
            return True
        if Vector.perp(u, v) != 0:
            return False

        try:
            k = v.x // u.x
        except ZeroDivisionError:
            k = v.y // u.y

        return k == 0

    @staticmethod
    def point_near_line(point, line, padding):
        if line.degenerate:
            return Collisions.points_nearby(point, line.head, padding)

        A, B = line.points
        C = point; R = padding

        a = (B.x - A.x)**2 + (B.y - A.y)**2
        b = 2 * (B.x - A.x) * (A.x - C.x)       \
                + 2 * (B.y - A.y) * (A.y - C.y)
        c = C.x**2 + C.y**2 + A.x**2 + A.y**2   \
                - 2 * (C.x * A.x + C.y * A.y) - R**2

        discriminant = b**2 - 4 * a * c

        if discriminant < 0:
            return False
        elif discriminant == 0:
            u = v = -b / float(2 * a)
        else:
            u = (-b + math.sqrt(discriminant)) / float(2 * a)
            v = (-b - math.sqrt(discriminant)) / float(2 * a)

        if u < 0 and v < 0: return False
        if u > 1 and v > 1: return False

        return True

    @staticmethod
    def point_past_line(point, line, padding=0):
        projection = Vector.dot(point - line.center, line.facing)
        return projection <= padding

    # Points and Shapes {{{1
    @staticmethod
    def point_near_circle(point, circle, padding):
        return Collisions.points_nearby(
                point, circle.center, circle.radius + padding)

    @staticmethod
    def point_near_shape(point, shape, padding):
        past_edge = Collisions.point_past_line

        for edge in shape.edges:
            if not past_edge(point, edge, padding):
                return False
        return True

    @staticmethod 
    def point_inside_circle(point, circle):
        return Collisions.point_near_circle(point, circle, 0)

    @staticmethod 
    def point_inside_shape(point, shape):
        return Collisions.point_near_shape(point, shape, 0)
    # }}}1

    # Lines Touching {{{1
    @staticmethod
    def lines_touching(first, second):

        # Returns true if a degenerate, collinear point is on a line.
        def within_bounds(point, line):
            start, end = line.points

            if start.x == end.x:
                if point.x <= start.x and point.x >= end.x: return True
                if point.x >= start.x and point.x <= end.x: return True
            else:
                if point.x <= start.x and point.x >= end.x: return True
                if point.x >= start.x and point.x <= end.x: return True

            return False

        u = first.direction
        v = second.direction

        w = first.tail - second.tail
        q = first.head - second.tail

        denom = float(Vector.perp(u, v))

        # Parallel, maybe coincident
        if denom == 0:
            # Check for coincidence
            if Vector.perp(u, w) != 0 or Vector.perp(v, w) != 0:
                return False

            # Check for degeneracy
            elif first.degenerate and second.degenerate:
                return (first.head == second.head)

            elif first.degenerate:
                return within_bounds(first.head, second)

            elif second.degenerate:
                return within_bounds(second.head, second)

            # Check for segment overlap
            else:
                try:
                    s = q.x / v.x
                    t = w.x / v.x
                except ZeroDivisionError:
                    s = q.y / v.y
                    t = w.y / v.y

                if s > t:
                    s, t = t, s

                if s > 1 or t < 0:
                    return False

                return True

        # Skew: maybe intersecting.
        else:

            s = Vector.perp(v, w) / denom
            if s < 0 or s > 1:
                return False

            t = Vector.perp(u, w) / denom
            if t < 0 or t > 1:
                return False

            return True

    # Lines and Shapes {{{1

    @staticmethod
    def circle_near_line(circle, line, padding):
        return Collisions.point_near_line(
                circle.center, line, circle.radius + padding)

    @staticmethod
    def circle_touching_line(circle, line):
        return Collisions.circle_near_line(circle, line, 0)

    @staticmethod
    def circle_past_line(circle, line, padding=0):
        return Collisions.point_past_line(
                circle.center, line, circle.radius + padding)

    @staticmethod
    def shape_touching_line(shape, line):
        lines_touching = Collisions.lines_touching
        for edge in shape.edges:
            if lines_touching(edge, line):
                return True
        return False

    @staticmethod
    def shape_past_line(shape, line, padding):
        point_past_line = Collisions.point_past_line
        for vertex in shape.vertices:
            if point_past_line(vertex, line, padding):
                return True
        return False
    # }}}1

    # Shapes Touching {{{1
    @staticmethod
    def circles_nearby(first, second, padding):
        distance = first.radius + second.radius + padding
        return Collisions.points_nearby(
                first.center, second.center, distance)

    @staticmethod
    def circles_touching(first, second):
        return Collisions.circles_nearby(first, second, 0)

    @staticmethod
    def circle_touching_shape(circle, shape):
        point_inside_shape = Collisions.point_inside_shape
        circle_touching_edge = Collisions.circle_touching_line

        if point_inside_shape(circle.center, shape):
            return True
        for edge in shape.edges:
            if circle_touching_edge(circle, edge):
                return True

        return False

    @staticmethod
    def shape_touching_circle(shape, circle):
        return Collisions.circle_touching_shape(circle, shape)

    @staticmethod
    def shapes_touching(first, second):

        # Optimized box/box collision
        if isinstance(first, shapes.Rectangle)   \
                and isinstance(second, shapes.Rectangle):

            if first.top > second.bottom: return False
            if first.bottom < second.top: return False

            if first.left > second.right: return False
            if first.right < second.left: return False

            return True

        # Generic shape/shape collision
        point_inside_shape = Collisions.point_inside_shape
        shape_touching_edge = Collisions.shape_touching_line

        if point_inside_shape(first.center, second): return True
        if point_inside_shape(second.center, first): return True

        for edge in first.edges:
            if shape_touching_edge(second, edge):
                return True

        return False
    # }}}1

if __name__ == "__main__":
    from shapes import *

    # Points and Lines {{{1
    def points_and_lines():

        origin = Vector(10, 10)
        degenerate = Line(origin, origin)
        line = Line(Vector(10, 5), Vector(10, 15), Vector(-1, 0))

        pairs = [(x, y) for x in range(5)
                        for y in range(5)]

        points_nearby = Collisions.points_nearby
        point_on_line = Collisions.point_on_line
        point_near_line = Collisions.point_near_line
        point_past_line = Collisions.point_past_line

        assert point_on_line(origin, degenerate)
                    
        near_point = [
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, True,  True,  True,  False],
                [False, False, True,  False, False],
                [False, False, False, False, False] ]

        on_line = [
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, False, True,  False, False],
                [False, False, True,  False, False],
                [False, False, False, False, False] ]
                
        near_line = [
                [False, False, True,  False, False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, False, True,  False, False] ]

        past_line = [
                [False, True,  True,  True,  True],
                [False, True,  True,  True,  True],
                [False, True,  True,  True,  True],
                [False, True,  True,  True,  True],
                [False, True,  True,  True,  True] ]

        try:
            for x, y in pairs:
                point = 5 * Vector(x, y)

                assert point_on_line(point, line) == on_line[y][x]
                assert point_near_line(point, line, 5) == near_line[y][x]
                assert point_past_line(point, line, 5) == past_line[y][x]

                assert points_nearby(point, origin, 5) == near_point[y][x]

        except AssertionError:
            print "An assertion failed at %s." % point; print
            raise

    # Points and Shapes {{{1
    def points_and_shapes():
        box = Rectangle(5, 5, 15, 15)
        circle = Circle(box.center, box.width / 2.0)

        zero_box = Rectangle(10, 10, 10, 10)
        zero_circle = Circle(box.center, 0)

        pairs = [(x, y) for x in range(5)
                        for y in range(5)]

        point_near_shape = Collisions.point_near_shape
        point_near_circle = Collisions.point_near_circle

        point_inside_shape = Collisions.point_inside_shape
        point_inside_circle = Collisions.point_inside_circle

        near_box = [
                [True, True, True, True, True],
                [True, True, True, True, True],
                [True, True, True, True, True],
                [True, True, True, True, True],
                [True, True, True, True, True] ]

        near_circle = [
                [False, False, True,  False, False],
                [False, True,  True,  True,  False],
                [True,  True,  True,  True,  True],
                [False, True,  True,  True,  False],
                [False, False, True,  False, False] ]

        inside_box = [
                [False, False, False, False, False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, False, False, False, False] ]

        inside_circle = [
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, True,  True,  True,  False],
                [False, False, True,  False, False],
                [False, False, False, False, False] ]

        inside_zero = [
                [False, False, False, False, False],
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, False, False, False, False],
                [False, False, False, False, False] ]

        for x, y in pairs:
            point = 5 * Vector(x, y)

            assert point_near_shape(point, box, 5) == near_box[y][x]
            assert point_near_circle(point, circle, 5) == near_circle[y][x]

            assert point_inside_shape(point, box) == inside_box[y][x]
            assert point_inside_circle(point, circle) == inside_circle[y][x]

            assert point_inside_shape(point, zero_box)      \
                    == inside_zero[y][x]
            assert point_inside_circle(point, zero_circle)  \
                    == inside_zero[y][x]
    # }}}1

    # Lines and Shapes {{{1
    def lines_and_shapes():
        lines_touching = Collisions.lines_touching
        shape_touching_line = Collisions.shape_touching_line
        circle_touching_line = Collisions.circle_touching_line

        # Test shapes.
        point = Vector(10, 10)

        intersect = Line(Vector(10, 10), Vector(10, 20))
        parallel = Line(Vector(5, 10), Vector(15, 10))
        zero = Line(Vector(10, 10), Vector(10, 10))

        box = Rectangle(5, 5, 15, 15)
        circle = Circle(Vector(10, 10), 5)

        zero_box = Rectangle.from_point(point)
        zero_circle = Circle(point, 0)

        pairs = [(left, right) for left in range(5)
                               for right in range(5)]

        touching_point = [
                [False, False, False, False, True],
                [False, False, False, True,  False],
                [False, False, True,  False, False],
                [False, True,  False, False, False],
                [True,  False, False, False, False] ]

        touching_intersect = [
                [False, False, False, False, True],
                [False, False, False, True,  True],
                [False, False, True,  True,  True],
                [False, True,  True,  True,  True],
                [True,  True,  True,  True,  True] ]

        touching_parallel = [
                [False, False, False, True,  True],
                [False, False, False, True,  True],
                [False, False, True,  False, False],
                [True,  True,  False, False, False],
                [True,  True,  False, False, False] ]

        touching_circle = [
                [False, False, True,  True,  True],
                [False, True,  True,  True,  True],
                [True,  True,  True,  True,  True],
                [True,  True,  True,  True,  False],
                [True,  True,  True,  False, False] ]

        touching_box = [
                [False, False, True,  True,  True],
                [False, True,  True,  True,  True],
                [True,  True,  True,  True,  True],
                [True,  True,  True,  True,  False],
                [True,  True,  True,  False, False] ]

        for left, right in pairs:
            start = Vector(0, 5 * left)
            end = Vector(20, 5 * right)
            line = Line(start, end)

            try:
                assert lines_touching(line, intersect)              \
                        == touching_intersect[left][right]
                assert lines_touching(intersect, line)              \
                        == touching_intersect[left][right]

                assert lines_touching(line, parallel)               \
                        == touching_parallel[left][right]
                assert lines_touching(parallel, line)               \
                        == touching_parallel[left][right]

                assert lines_touching(line, zero)                   \
                        == touching_point[left][right]

                assert shape_touching_line(box, line)               \
                        == touching_box[left][right]
                assert circle_touching_line(circle, line)           \
                        == touching_circle[left][right]

                assert shape_touching_line(zero_box, line)          \
                        == touching_point[left][right]
                assert circle_touching_line(zero_circle, line)      \
                        == touching_point[left][right]

            except AssertionError:
                print "\nAssertion at L:%d R:%d failed.\n" % (left, right)
                raise

        # Test degenerate lines.
        coordinates = (5, 10, 15)
        results = (False, True, False)

        for x, result in zip(coordinates, results):
            point = Vector(x, 10)
            line = Line(point, point)

            assert lines_touching(zero, line) == result
            assert lines_touching(line, zero) == result

        # Test parallel lines.
        coordinates = (5, 10, 15)
        results = (False, True, True)

        standards = (
                Line(Vector(10, 0), Vector(15, 0)),
                Line(Vector(15, 0), Vector(10, 0)) )

        for coordinate, result in zip(coordinates, results):

            comparisons = (
                    Line(Vector.null(), Vector(coordinate, 0)),
                    Line(Vector(coordinate, 0), Vector.null()) )

            for standard in standards:
                for comparison in comparisons:
                    assert lines_touching(standard, comparison) == result
                    assert lines_touching(comparison, standard) == result

    # Shapes and Circles {{{1
    def shapes_and_circles():
        circle_3 = Circle(Vector(10, 10), 3)
        rect_3 = Rectangle.from_circle(circle_3)

        pairs = [(x, y) for x in range(5)
                        for y in range(5)]

        shapes_touching = Collisions.shapes_touching
        circle_touching_shape = Collisions.circle_touching_shape
        circles_touching = Collisions.circles_touching
                    
        touching_rect = [
                [False, False, False, False, False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, True,  True,  True,  False],
                [False, False, False, False, False] ]
                    
        touching_circle = [
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, True,  True,  True,  False],
                [False, False, True,  False, False],
                [False, False, False, False, False] ]

        touching_zero = [
                [False, False, False, False, False],
                [False, False, False, False, False],
                [False, False, True,  False, False],
                [False, False, False, False, False],
                [False, False, False, False, False] ]

        for x, y in pairs:
            circle_2 = Circle(5 * Vector(x, y), 2)
            rect_2 = Rectangle.from_circle(circle_2)
            polygon_2 = Polygon.from_vertices(rect_2.vertices)

            circle_0 = Circle(5 * Vector(x, y), 0)
            rect_0 = Rectangle.from_circle(circle_0)

            # Testing against a rect
            assert shapes_touching(rect_3, rect_2) == touching_rect[y][x]
            assert shapes_touching(rect_3, rect_0) == touching_zero[y][x]

            assert shapes_touching(rect_3, polygon_2) == touching_rect[y][x]
            assert shapes_touching(polygon_2, rect_3) == touching_rect[y][x]

            assert circle_touching_shape(circle_2, rect_3) ==        \
                    touching_circle[y][x]
            assert circle_touching_shape(circle_0, rect_3) ==        \
                    touching_zero[y][x]

            # Testing against a circle
            assert circles_touching(circle_3, circle_2) ==          \
                    touching_circle[y][x]
            assert circles_touching(circle_3, circle_0) ==          \
                    touching_zero[y][x]

            assert circle_touching_shape(circle_3, rect_2) ==        \
                    touching_circle[y][x]
            assert circle_touching_shape(circle_3, rect_0) ==        \
                    touching_zero[y][x]
    # }}}1

    print "Testing collisions.py..."

    points_and_lines()
    points_and_shapes()

    lines_and_shapes()
    shapes_and_circles()

    print "All tests passed."
