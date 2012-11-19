from __future__ import division

import math
import random
import operator

infinity = inf = float('inf')
golden_ratio = 1/2 + math.sqrt(5) / 2

# Private Helper Functions

def _cast_vector_type(input):
    if isinstance(input, Vector): return input
    try: return Vector(*input)
    except: raise VectorCastError(input)

def _cast_vector_or_scalar_type(input):
    if isinstance(input, Vector): return input
    try: return Vector(*input)
    except: return Vector(input, input)

def _accept_vector_type(function):
    def decorator(self, input):
        vector = cast_vector_type(input)
        return function(vector)
    return decorator

def _accept_vector_or_scalar_type(function):
    def decorator(self, input):
        vector = cast_vector_or_scalar_type(input)
        return function(vector)
    return decorator

def _overload_left_side(f):
    def operator(a, b):
        try: return Vector(f(a.x, b.x), f(a.y, b.y))
        except: pass

        try: return Vector(f(a.x, b[0]), f(a.y, b[1]))
        except: pass

        try: return Vector(f(a.x, b), f(a.y, b))
        except: pass

        raise VectorCastError(b)

    return operator

def _overload_right_side(f):
    def operator(a, b):
        try: return Vector(f(b.x, a.x), f(b.y, a.y))
        except: pass

        try: return Vector(f(b[0], a.x), f(b[1], a.y))
        except: pass

        try: return Vector(f(b, a.x), f(b, a.y))
        except: pass

        raise VectorCastError(b)

    return operator

def _overload_in_place(f):
    def operator(a, b):
        try: a.x, a.y = f(a.x, b.x), f(a.y, b.y)
        except: pass

        try: a.x, a.y = f(a.x, b[0]), f(a.y, b[1])
        except: pass

        try: a.x, a.y = f(a.x, b), f(a.y, b)
        except: pass

        raise VectorCastError(b)

    return operator


# Shape Classes

class Shape (object):

    def get_left(self):
        raise NotImplementedError

    def get_right(self):
        raise NotImplementedError

    def get_top(self):
        raise NotImplementedError

    def get_bottom(self):
        raise NotImplementedError


class Rectangle (Shape):

    def __init__(self, left, top, width, height):
        self.__left = left
        self.__top = top
        self.__width = width
        self.__height = height

    def __repr__(self):
        return "Rectangle(%d, %d, %d, %d)" % self.tuple

    def __str__(self):
        return "Rectangle: (%d, %d), %dx%d" % self.tuple

    def __eq__(self, other):
        return ( self.__top == other.__top and
                 self.__left == other.__left and
                 self.__width == other.__width and
                 self.__height == other.__height )

    def __contains__(self, other):
        return self.contains(other)


    @staticmethod
    def from_size(width, height):
        return Rectangle(0, 0, width, height)

    @staticmethod
    def from_width(width, ratio=1/golden_ratio):
        return Rectangle.from_size(width, ratio * width)

    @staticmethod
    def from_height(height, ratio=golden_ratio):
        return Rectangle.from_size(ratio * height, height)

    @staticmethod
    def from_square(size):
        return Rectangle.from_size(size, size)

    @staticmethod
    def from_dimensions(left, top, width, height):
        return Rectangle(left, top, width, height)

    @staticmethod
    def from_sides(left, top, right, bottom):
        width = right - left; height = bottom - right
        return Rectangle.from_dimensions(left, right, width, height)

    @staticmethod
    def from_center(position, width, height):
        return Rectangle(position.x, position.y, width, height)

    @staticmethod
    def from_surface(surface):
        width, height = surface.get_size()
        return Rectangle.from_size(width, height)
    
    @staticmethod
    def from_union(*rectangles):
        left = min(x.left for x in rectangles)
        top = min(x.top for x in rectangles)
        right = max(x.right for x in rectangles)
        bottom = max(x.bottom for x in rectangles)

        return Rectangle.from_sides(left, top, right, bottom)

    @staticmethod
    def from_intersection(*rectangles):
        left = max(x.left for x in rectangles)
        top = max(x.top for x in rectangles)
        right = min(x.right for x in rectangles)
        bottom = min(x.bottom for x in rectangles)

        return Rectangle.from_sides(left, top, right, bottom)


    def grow(self, padding):
        self.__top += padding
        self.__left += padding
        self.__width += 2 * padding
        self.__height += 2 * padding

    def shrink(self, padding):
        self.__top -= padding
        self.__left -= padding
        self.__width -= 2 * padding
        self.__height -= 2 * padding

    def displace(self, displacement):
        self.top += displacement[0]
        self.left += displacement[1]

    def clone(self):
        from copy import deepcopy
        return deepcopy(self)


    def align_left(self, target):
        self.left = target.left

    def align_center_x(self, target):
        self.center_x = target.center_x

    def align_right(self, target):
        self.right = target.right

    def align_top(self, target):
        self.top = target.top

    def align_center_y(self, target):
        self.center_y = target.center_y

    def align_bottom(self, target):
        self.bottom = target.bottom


    def inside(self, other):
        """ Return true if this rectangle is inside the given shape. """
        return ( self.left < other.left and
                 self.right > other.right and
                 self.top < other.top and
                 self.bottom > other.bottom )

    def outside(self, other):
        """ Return if this rectangle is outside the given shape. """
        raise NotImplementedError

    def touching(self, other):
        """ Return true if this rectangle is touching the given shape. """
        raise NotImplementedError

    def contains(self, other):
        """ Return true if the given shape is inside this rectangle. """
        raise NotImplementedError


    def get_left(self):
        return self.__left

    def get_center_x(self):
        return self.__left + self.__width / 2

    def get_right(self):
        return self.__left + self.__width

    def get_top(self):
        return self.__top

    def get_center_y(self):
        return self.__top + self.__bottom / 2

    def get_bottom(self):
        return self.__top + self.__height

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height

    def get_size(self):
        return self.__width, self.__height


    def get_top_left(self):
        return Vector(self.left, self.top)

    def get_top_center(self):
        return Vector(self.center_x, self.top)

    def get_top_right(self):
        return Vector(self.right, self.top)

    def get_center_left(self):
        return Vector(self.left, self.center_y)

    def get_center(self):
        return Vector(self.center_x, self.center_y)

    def get_center_right(self):
        return Vector(self.right, self.center_y)

    def get_bottom_left(self):
        return Vector(self.left, self.bottom)

    def get_bottom_center(self):
        return Vector(self.center_x, self.bottom)

    def get_bottom_right(self):
        return Vector(self.right, self.bottom)


    def get_dimensions(self):
        return (self.__left, self.__top), (self.__width, self.__height)

    def get_tuple(self):
        return self.__left, self.__top, self.__width, self.__height

    def get_pygame(self):
        from pygame.rect import Rect
        return Rect(self.left, self.top, self.width, self.height)

    def get_union(self, *rectangles):
        raise NotImplementedError

    def get_intersection(self, *rectangles):
        raise NotImplementedError


    def set_left(self, x):
        self.__left = x

    def set_center_x(self, x):
        self.__left = x - self.__width / 2

    def set_right(self, x):
        self.__left = x - self.__width

    def set_top(self, y):
        self.__top = y

    def set_center_y(self, y):
        self.__top = y - self.__height / 2

    def set_bottom(self, y):
        self.__top = y - self.__height

    def set_width(self, width):
        self.__width = width

    def set_height(self, height):
        self.__height = height

    def set_size(self, width, height):
        self.__width = width
        self.__height = height


    def set_top_left(self, point):
        self.top = point[1]
        self.left = point[0]

    def set_top_center(self, point):
        self.top = point[1]
        self.center_x = point[0]

    def set_top_right(self, point):
        self.top = point[1]
        self.right = point[0]

    def set_center_left(self, point):
        self.center_y = point[1]
        self.left = point[0]

    def set_center(self, point):
        self.center_y = point[1]
        self.center_x = point[0]

    def set_center_right(self, point):
        self.center_y = point[1]
        self.right = point[0]

    def set_bottom_left(self, point):
        self.bottom = point[1]
        self.left = point[0]

    def set_bottom_center(self, point):
        self.bottom = point[1]
        self.center_x = point[0]

    def set_bottom_right(self, point):
        self.bottom = point[1]
        self.right = point[0]


    # Properties (fold)
    left = property(get_left, set_left)
    center_x = property(get_center_x, set_center_x)
    right = property(get_right, set_right)
    top = property(get_top, set_top)
    center_y = property(get_center_y, set_center_y)
    bottom = property(get_bottom, set_bottom)
    width = property(get_width, set_width)
    height = property(get_height, set_height)
    size = property(get_size, set_size)

    top_left = property(get_top_left, set_top_left)
    top_center = property(get_top_center, set_top_center)
    top_right = property(get_top_right, set_top_right)
    center_left = property(get_center_left, set_center_left)
    center = property(get_center, set_center)
    center_right = property(get_center_right, set_center_right)
    bottom_left = property(get_bottom_left, set_bottom_left)
    bottom_center = property(get_bottom_center, set_bottom_center)
    bottom_right = property(get_bottom_right, set_bottom_right)

    dimensions = property(get_dimensions)
    tuple = property(get_tuple)
    pygame = property(get_pygame)


class Vector (Shape):
    """ Represents a two-dimensional vector.  In particular, this class
    features a number of factory methods to create vectors from angles and
    other input and a number of overloaded operators to facilitate vector
    math. """

    @staticmethod
    def null():
        """ Return a null vector. """
        return Vector(0, 0)

    @staticmethod
    def random(magnitude=1):
        """ Create a unit vector pointing in a random direction. """
        theta = random.uniform(0, 2 * math.pi)
        return magnitude * Vector(math.cos(theta), math.sin(theta))

    @staticmethod
    def from_radians(angle):
        """ Create a vector that makes the given angle with the x-axis. """
        return Vector(math.cos(angle), math.sin(angle))

    @staticmethod
    def from_degrees(angle):
        """ Create a vector that makes the given angle with the x-axis. """
        return Vector.from_radians(angle * math.pi / 180)

    @staticmethod
    def from_tuple(coordinates):
        """ Create a vector from a two element tuple. """
        return Vector(*coordinates)

    @staticmethod
    def from_scalar(scalar):
        """ Create a vector from a single scalar value. """
        return Vector(scalar, scalar)

    @staticmethod
    def from_rectangle(box):
        """ Create a vector randomly within the given rectangle. """
        x = box.left + box.width * random.uniform(0, 1)
        y = box.top + box.height * random.uniform(0, 1)
        return Vector(x, y)


    def normalize(self):
        """ Set the magnitude of this vector to unity, in place. """
        try:
            self /= self.magnitude
        except ZeroDivisionError:
            raise NullVectorError

    def interpolate(self, target, extent):
        """ Move this vector towards the given towards the target by the given 
        extent.  The extent should be between 0 and 1. """
        result = self.get_interpolated(target, extent)
        self.x, self.y = result.x, result.y

    @_accept_vector_type
    def dot_product(self, other):
        """ Return the dot product of the given vectors. """
        return self.x * other.x + self.y * other.y

    @_accept_vector_type
    def perp_product(self, other):
        """ Return the perp product of the given vectors.  The perp product is
        just a cross product where the third dimension is taken to be zero and
        the result is returned as a scalar. """

        return self.x * other.y - self.y * other.x


    def __init__(self, x, y):
        """ Construct a vector using the given coordinates. """
        self.x = x
        self.y = y

    def __repr__(self):
        """ Return a string representation of this vector. """
        return "Vector(%f, %f)" % self.get_tuple()

    def __str__(self):
        """ Return a string representation of this vector. """
        return "<%f, %f>" % self.get_tuple()

    def __iter__(self):
        """ Iterate over this vectors coordinates. """
        yield self.x; yield self.y

    def __nonzero__(self):
        """ Return true is the vector is not degenerate. """
        return self.x != 0 or self.y != 0

    def __getitem__(self, i):
        """ Return the specified coordinate. """
        return self.tuple[i]

    def __neg__(self):
        """ Return a copy of this vector with the signs flipped. """
        return Vector(-self.x, -self.y)

    def __abs__(self):
        """ Return the absolute value of this vector. """
        return Vector(abs(self.x), abs(self.y))
    

    # Binary Operators (fold)
    __eq__ = _overload_left_side(operator.eq)
    __ne__ = _overload_left_side(operator.ne)

    __add__ = _overload_left_side(operator.add)
    __radd__ = _overload_right_side(operator.add)
    __iadd__ = _overload_in_place(operator.add)

    __sub__ = _overload_left_side(operator.sub)
    __rsub__ = _overload_right_side(operator.sub)
    __isub__ = _overload_in_place(operator.sub)

    __mul__ = _overload_left_side(operator.mul)
    __rmul__ = _overload_right_side(operator.mul)
    __imul__ = _overload_in_place(operator.mul)

    __div__ = _overload_left_side(operator.div)
    __rdiv__ = _overload_right_side(operator.div)
    __idiv__ = _overload_in_place(operator.div)

    __floordiv__ = _overload_left_side(operator.floordiv)
    __rfloordiv__ = _overload_right_side(operator.floordiv)
    __ifloordiv__ = _overload_in_place(operator.floordiv)

    __truediv__ = _overload_left_side(operator.truediv)
    __rtruediv__ = _overload_right_side(operator.truediv)
    __itruediv__ = _overload_in_place(operator.truediv)
    
    __mod__ = _overload_left_side(operator.mod)
    __rmod__ = _overload_right_side(operator.mod)
    __imod__ = _overload_in_place(operator.mod)

    __pow__  = _overload_left_side(operator.pow)
    __rpow__  = _overload_right_side(operator.pow)
    __ipow__  = _overload_in_place(operator.pow)


    def get_left(self):
        """ Get the x coordinate of this vector. """
        return self.x

    def get_right(self):
        """ Get the x coordinate of this vector. """
        return self.x

    def get_top(self):
        """ Get the y coordinate of this vector. """
        return self.y

    def get_bottom(self):
        """ Get the y coordinate of this vector. """
        return self.y

    def get_tuple(self):
        """ Return the vector as a tuple. """
        return self.x, self.y

    def get_pygame(self):
        """ Return the vector as a tuple of integers.  This is the format
        Pygame expects to receive coordinates in. """
        return int(self.x), int(self.y)

    def get_magnitude(self):
        """ Calculate the length of this vector. """
        return math.sqrt(self.magnitude_squared)

    def get_magnitude_squared(self):
        """ Calculate the square of the length of this vector.  This is
        slightly more efficient that finding the real length. """
        return self.x**2 + self.y**2

    @_accept_vector_type
    def get_distance(self, other):
        """ Return the Euclidean distance between the two input vectors. """
        return (other - self).magnitude

    @_accept_vector_type
    def get_manhattan(self, other):
        """ Return the Manhattan distance between the two input vectors. """
        return sum(abs(other - self))

    def get_normal(self):
        """ Return a unit vector parallel to this one. """
        try:
            return self / self.magnitude
        except ZeroDivisionError:
            raise NullVectorError()

    def get_orthogonal(self):
        """ Return a vector that is orthogonal to this one.  The resulting
        vector is not normalized. """
        return Vector(-self.y, self.x)

    def get_orthonormal(self):
        """ Return a vector that is both normalized and orthogonal to this
        one. """
        return self.orthogonal.normal

    def get_interpolated(self, target, extent):
        """ Return a new vector that has been moved towards the given target by 
        the given extent.  The extent should be between 0 and 1. """
        target = _cast_vector_type(target)
        return self + extent * (target - self)

    @_accept_vector_type
    def get_components(self, other):
        """ Break this vector into one vector that is parallel to the given
        vector and another that is perpendicular to it. """

        tangent = other * Vector.dot(self, other)
        normal = self - tangent
        return normal, tangent

    def get_radians(self):
        raise NotImplementedError

    def get_degrees(self):
        raise NotImplementedError

    @_accept_vector_type
    def get_radians_to(self, other):
        """ Return the angle between the two given vectors in degrees.  If
        either of the inputs are null vectors, an exception is thrown. """

        try:
            temp = self.magnitude * other.magnitude
            temp = self.dot(other) / temp
            return math.acos(temp)

        # Floating point error will confuse the trig functions occasionally.
        except ValueError:
            return 0 if temp > 0 else pi

        # It doesn't make sense to find the angle of a null vector. 
        except ZeroDivisionError:
            raise NullVectorError()

    @_accept_vector_type
    def get_degrees_to(self, other):
        """ Return the angle between the two given vectors in degrees.  If
        either of the inputs are null vectors, an exception is thrown. """
        return self.get_radians_to(other) * 180 / math.pi


    def set_left(self, x):
        """ Set the x coordinate of this vector. """
        self.x = x

    def set_right(self, x):
        """ Set the x coordinate of this vector. """
        self.x = x

    def set_top(self, y):
        """ Set the y coordinate of this vector. """
        self.y = y

    def set_bottom(self, y):
        """ Set the y coordinate of this vector. """
        self.y = y

    def set_radians(self, angle):
        """ Set the angle that this vector makes with the x-axis. """
        self.x, self.y = math.cos(angle), math.sin(angle)

    def set_degrees(self, angle):
        """ Set the angle that this vector makes with the x-axis. """
        self.set_radians(angle * math.pi / 180)

    def set_tuple(self, coordinates):
        """ Set the x and y coordinates of this vector. """
        self.x, self.y = coordinates
    
    def set_magnitude(self, magnitude):
        """ Set the magnitude of this vector in place. """
        self.normalize()
        self *= magnitude


    # Aliases (fold)
    dot = dot_product
    perp = perp_product

    # Properties (fold)
    tuple = property(get_tuple, set_tuple)
    pygame = property(get_pygame)

    magnitude = property(get_magnitude, set_magnitude)
    magnitude_squared = property(get_magnitude_squared)

    normal = property(get_normal)
    orthogonal = property(get_orthogonal)
    orthonormal = property(get_orthonormal)

    radians = property(get_radians, set_radians)
    degrees = property(get_degrees, set_degrees)



# Exception Classes

class NullVectorError (Exception):
    """ Thrown when an operation chokes on a null vector. """
    pass

class VectorCastError (Exception):
    """ Thrown an inappropriate object is used as a vector. """

    def __init__(self, object):
        Exception.__init__("Could not cast %s to vector." % type(object))



