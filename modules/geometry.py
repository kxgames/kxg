from __future__ import division

import math
import random
import operator

infinity = inf = float('inf')
golden_ratio = 1/2 + math.sqrt(5) / 2

# Private Helper Functions

def _cast_anything_to_vector(input):
    if isinstance(input, Vector):
        return input
    try:
        return Vector(*input)
    except:
        raise VectorCastError(input)

def _cast_anything_to_rectangle(input):

    # If the input object implements the shape interface, use that information 
    # to directly return a rectangle object.
    
    try: return _cast_shape_to_rectangle(input)
    except: pass

    # If the input object can be cast to a vector, try to represent that vector 
    # as a rectangle.  Such a rectangle is located where the vector points and 
    # has no area (i.e. width = height = 0).

    try: return Rectangle.from_vector(input)
    except: pass

    # If the function has returned by now, the input object could not be cast 
    # to a rectangle.  Throw an exception.

    raise RectangleCastError(input)

def _cast_shape_to_rectangle(input):

    if isinstance(input, Rectangle):
        return input

    # If the input object implements the shape interface (i.e. has top, left, 
    # width, and height attributes), use that information to construct a bona 
    # fide rectangle object.

    try: return Rectangle.from_shape(input)
    except: pass

    raise RectangleCastError(input)

def _accept_anything_as_vector(function):
    def decorator(self, input):
        vector = _cast_anything_to_vector(input)
        return function(self, vector)
    return decorator

def _accept_anything_as_rectangle(function):
    def decorator(self, input):
        rect = _cast_anything_to_rectangle(input)
        return function(self, rect)
    return decorator

def _accept_shape_as_rectangle(function):
    def decorator(self, input):
        rect = _cast_shape_to_rectangle(input)
        return function(self, rect)
    return decorator

def _overload_left_side(f, scalar_ok=False):
    def operator(self, other):
        try: x, y = other.x, other.y
        except: pass
        else: return Vector(f(self.x, x), f(self.y, y))

        try: x, y = other
        except: pass
        else: return Vector(f(self.x, x), f(self.y, y))

        # Zero is treated as a special case, because the built-in sum() 
        # function expects to be able to add zero to things.
        
        if (other is 0) or (scalar_ok):
            return Vector(f(self.x, other), f(self.y, other))
        else:
            raise VectorCastError(other)

    return operator

def _overload_right_side(f, scalar_ok=False):
    def operator(self, other):
        try: x, y = other
        except: pass
        else: return Vector(f(x, self.x), f(y, self.y))

        # This block is intended mostly for other vectors.  However, if the 
        # right-side operator is being invoked, then the operand is more likely 
        # to be a tuple than some other object with x and y attributes.  So it 
        # makes sense to check for a tuple first.  
        
        try: x, y = other.x, other.y
        except: pass
        else: return Vector(f(x, self.x), f(y, self.y))

        if (other is 0) or (scalar_ok):
            return Vector(f(other, self.x), f(other, self.y))
        else:
            raise VectorCastError(other)

    return operator

def _overload_in_place(f, scalar_ok=False):
    def operator(self, other):
        try: x, y = other.x, other.y
        except: pass
        else: self.x, self.y = f(self.x, x), f(self.y, y); return self

        try: x, y = other
        except: pass
        else: self.x, self.y = f(self.x, x), f(self.y, y); return self

        if (other is 0) or (scalar_ok):
            self.x, self.y = f(self.x, other), f(self.y, other)
            return self
        else:
            raise VectorCastError(other)

    return operator


# Vector and Rectangle Classes

class Shape (object):
    """ Provide an interface for custom shape classes to interact with the 
    rectangle class.  For example, rectangles can be instantiated from shapes
    and can test for collisions against shapes.  The interface is very simple,
    requiring only four methods to be redefined. """

    def get_top(self):
        raise NotImplementedError

    def get_left(self):
        raise NotImplementedError

    def get_width(self):
        raise NotImplementedError

    def get_height(self):
        raise NotImplementedError


    # Properties (fold)
    top = property(get_top)
    left = property(get_left)
    width = property(get_width)
    height = property(get_height)


class Vector (object):
    """ Represents a two-dimensional vector.  In particular, this class
    features a number of factory methods to create vectors from various inputs
    and a number of overloaded operators to facilitate vector arithmetic. """

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


    def copy(self):
        """ Return a copy of this vector. """
        from copy import deepcopy
        return deepcopy(self)

    @_accept_anything_as_vector
    def assign(self, other):
        """ Copy the given vector into this one. """
        self.x, self.y = other.tuple

    def normalize(self):
        """ Set the magnitude of this vector to unity, in place. """
        try:
            self /= self.magnitude
        except ZeroDivisionError:
            raise NullVectorError

    def scale(self, magnitude):
        """ Set the magnitude of this vector in place. """
        self.normalize()
        self *= magnitude

    def interpolate(self, target, extent):
        """ Move this vector towards the given towards the target by the given 
        extent.  The extent should be between 0 and 1. """
        target = _cast_anything_to_vector(target)
        self += extent * (target - self)

    @_accept_anything_as_vector
    def project(self, axis):
        """ Project this vector onto the given axis. """
        projection = self.get_projection(axis)
        self.assign(projection)

    @_accept_anything_as_vector
    def dot_product(self, other):
        """ Return the dot product of the given vectors. """
        return self.x * other.x + self.y * other.y

    @_accept_anything_as_vector
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
        return "<%.2f, %.2f>" % self.get_tuple()

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

    __mul__ = _overload_left_side(operator.mul, scalar_ok=True)
    __rmul__ = _overload_right_side(operator.mul, scalar_ok=True)
    __imul__ = _overload_in_place(operator.mul, scalar_ok=True)

    __div__ = _overload_left_side(operator.div, scalar_ok=True)
    __rdiv__ = _overload_right_side(operator.div, scalar_ok=True)
    __idiv__ = _overload_in_place(operator.div, scalar_ok=True)

    __floordiv__ = _overload_left_side(operator.floordiv, scalar_ok=True)
    __rfloordiv__ = _overload_right_side(operator.floordiv, scalar_ok=True)
    __ifloordiv__ = _overload_in_place(operator.floordiv, scalar_ok=True)

    __truediv__ = _overload_left_side(operator.truediv, scalar_ok=True)
    __rtruediv__ = _overload_right_side(operator.truediv, scalar_ok=True)
    __itruediv__ = _overload_in_place(operator.truediv, scalar_ok=True)
    
    __mod__ = _overload_left_side(operator.mod, scalar_ok=True)
    __rmod__ = _overload_right_side(operator.mod, scalar_ok=True)
    __imod__ = _overload_in_place(operator.mod, scalar_ok=True)

    __pow__  = _overload_left_side(operator.pow, scalar_ok=True)
    __rpow__  = _overload_right_side(operator.pow, scalar_ok=True)
    __ipow__  = _overload_in_place(operator.pow, scalar_ok=True)


    def get_x(self):
        """ Get the x coordinate of this vector. """
        return self.x

    def get_y(self):
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

    @_accept_anything_as_vector
    def get_distance(self, other):
        """ Return the Euclidean distance between the two input vectors. """
        return (other - self).magnitude

    @_accept_anything_as_vector
    def get_manhattan(self, other):
        """ Return the Manhattan distance between the two input vectors. """
        return sum(abs(other - self))

    def get_normal(self):
        """ Return a unit vector parallel to this one. """
        result = self.copy()
        result.normalize()
        return result

    def get_orthogonal(self):
        """ Return a vector that is orthogonal to this one.  The resulting
        vector is not normalized. """
        return Vector(-self.y, self.x)

    def get_orthonormal(self):
        """ Return a vector that is orthogonal to this one and that has been 
        normalized. """
        return self.orthogonal.normal

    def get_scaled(self, magnitude):
        """ Return a unit vector parallel to this one. """
        result = self.copy()
        result.scale(magnitude)
        return result

    def get_interpolated(self, target, extent):
        """ Return a new vector that has been moved towards the given target by 
        the given extent.  The extent should be between 0 and 1. """
        result = self.copy()
        result.interpolate(target, extent)
        return result

    @_accept_anything_as_vector
    def get_projection(self, axis):
        """ Return the projection of this vector onto the given axis.  The 
        axis does not need to be normalized. """
        scale = axis.dot(self) / axis.dot(axis)
        return axis * scale

    @_accept_anything_as_vector
    def get_components(self, other):
        """ Break this vector into one vector that is perpendicular to the 
        given vector and another that is parallel to it. """
        tangent = self.get_projection(other)
        normal = self - tangent
        return normal, tangent

    def get_radians(self):
        """ Return the angle between this vector and the positive x-axis 
        measured in radians. """
        if not self: raise NullVectorError()
        return math.atan2(self.y, self.x)

    def get_degrees(self):
        """ Return the angle between this vector and the positive x-axis 
        measured in degrees. """
        return self.radians * 180 / math.pi

    @_accept_anything_as_vector
    def get_radians_to(self, other):
        """ Return the angle between the two given vectors in radians.  If
        either of the inputs are null vectors, an exception is thrown. """
        return other.radians - self.radians

    @_accept_anything_as_vector
    def get_degrees_to(self, other):
        """ Return the angle between the two given vectors in degrees.  If
        either of the inputs are null vectors, an exception is thrown. """
        return other.degrees - self.degrees


    def set_x(self, x):
        """ Set the x coordinate of this vector. """
        self.x = x

    def set_y(self, y):
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
    

    # Aliases (fold)
    dot = dot_product
    perp = perp_product

    # Properties (fold)
    tuple = property(get_tuple, set_tuple)
    pygame = property(get_pygame)

    magnitude = property(get_magnitude, scale)
    magnitude_squared = property(get_magnitude_squared)

    normal = property(get_normal)
    orthogonal = property(get_orthogonal)
    orthonormal = property(get_orthonormal)

    radians = property(get_radians, set_radians)
    degrees = property(get_degrees, set_degrees)


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

    @_accept_anything_as_vector
    def __add__(self, vector):
        result = self.copy()
        result.displace(vector)
        return result

    @_accept_anything_as_vector
    def __iadd__(self, vector):
        self.displace(vector)
        return self

    @_accept_anything_as_vector
    def __sub__(self, vector):
        result = self.copy()
        result.displace(-vector)
        return result

    @_accept_anything_as_vector
    def __isub__(self, vector):
        self.displace(-vector)
        return self

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
        width = right - left; height = bottom - top
        return Rectangle.from_dimensions(left, top, width, height)

    @staticmethod
    def from_corners(first, second):
        first = _cast_anything_to_vector(first)
        second = _cast_anything_to_vector(second)

        left = min(first.x, second.x);  top = min(first.y, second.y)
        right = max(first.x, second.x); bottom = max(first.y, second.y)

        return Rectangle.from_sides(left, top, right, bottom)

    @staticmethod
    def from_top_left(position, width, height):
        position = _cast_anything_to_vector(position)
        return Rectangle(position.x, position.y, width, height)

    @staticmethod
    def from_center(position, width, height):
        position = _cast_anything_to_vector(position) - (width/2, height/2)
        return Rectangle(position.x, position.y, width, height)

    @staticmethod
    def from_vector(position):
        position = _cast_anything_to_vector(position)
        return Rectangle(position.x, position.y, 0, 0)

    @staticmethod
    def from_points(*points):
        left = min(_cast_anything_to_vector(p).x for p in points)
        top = min(_cast_anything_to_vector(p).y for p in points)
        right = max(_cast_anything_to_vector(p).x for p in points)
        bottom = max(_cast_anything_to_vector(p).y for p in points)
        return Rectangle.from_sides(left, top, right, bottom)

    @staticmethod
    def from_shape(shape):
        top, left = shape.top, shape.left
        width, height = shape.width, shape.height
        return Rectangle(left, top, width, height)

    @staticmethod
    def from_surface(surface):
        width, height = surface.get_size()
        return Rectangle.from_size(width, height)
    
    @staticmethod
    def from_union(*inputs):
        rectangles = [_cast_shape_to_rectangle(x) for x in inputs]
        left = min(x.left for x in rectangles)
        top = min(x.top for x in rectangles)
        right = max(x.right for x in rectangles)
        bottom = max(x.bottom for x in rectangles)
        return Rectangle.from_sides(left, top, right, bottom)

    @staticmethod
    def from_intersection(*inputs):
        rectangles = [_cast_shape_to_rectangle(x) for x in inputs]
        left = max(x.left for x in rectangles)
        top = max(x.top for x in rectangles)
        right = min(x.right for x in rectangles)
        bottom = min(x.bottom for x in rectangles)
        return Rectangle.from_sides(left, top, right, bottom)


    def grow(self, padding):
        """ Grow this rectangle by the given padding on all sides. """
        self.__top -= padding
        self.__left -= padding
        self.__width += 2 * padding
        self.__height += 2 * padding

    def shrink(self, padding):
        """ Shrink this rectangle by the given padding on all sides. """
        self.grow(-padding)

    @_accept_anything_as_vector
    def displace(self, vector):
        """ Displace this rectangle by the given vector. """
        self.__top += vector.y
        self.__left += vector.x

    def copy(self):
        """ Return a copy of this rectangle. """
        from copy import deepcopy
        return deepcopy(self)


    @_accept_shape_as_rectangle
    def inside(self, other):
        """ Return true if this rectangle is inside the given shape. """
        return ( self.left >= other.left and
                 self.right <= other.right and
                 self.top >= other.top and
                 self.bottom <= other.bottom )

    @_accept_anything_as_rectangle
    def outside(self, other):
        """ Return true if this rectangle is outside the given shape. """
        return not self.touching(other)

    @_accept_anything_as_rectangle
    def touching(self, other):
        """ Return true if this rectangle is touching the given shape. """
        if self.top > other.bottom: return False
        if self.bottom < other.top: return False

        if self.left > other.right: return False
        if self.right < other.left: return False

        return True

    @_accept_anything_as_rectangle
    def contains(self, other):
        """ Return true if the given shape is inside this rectangle. """
        return ( self.left <= other.left and
                 self.right >= other.right and
                 self.top <= other.top and
                 self.bottom >= other.bottom )


    @_accept_anything_as_rectangle
    def align_left(self, target):
        self.left = target.left

    @_accept_anything_as_rectangle
    def align_center_x(self, target):
        self.center_x = target.center_x

    @_accept_anything_as_rectangle
    def align_right(self, target):
        self.right = target.right

    @_accept_anything_as_rectangle
    def align_top(self, target):
        self.top = target.top

    @_accept_anything_as_rectangle
    def align_center_y(self, target):
        self.center_y = target.center_y

    @_accept_anything_as_rectangle
    def align_bottom(self, target):
        self.bottom = target.bottom


    def get_left(self):
        return self.__left

    def get_center_x(self):
        return self.__left + self.__width / 2

    def get_right(self):
        return self.__left + self.__width

    def get_top(self):
        return self.__top

    def get_center_y(self):
        return self.__top + self.__height / 2

    def get_bottom(self):
        return self.__top + self.__height

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height

    def get_size(self):
        return self.__width, self.__height

    def get_size_as_int(self):
        from math import ceil
        return int(ceil(self.__width)), int(ceil(self.__height))


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
        return Rectangle.from_union(self, *rectangles)

    def get_intersection(self, *rectangles):
        return Rectangle.from_intersection(self, *rectangles)

    def get_grown(self, padding):
        result = self.copy()
        result.grow(padding)
        return result

    def get_shrunk(self, padding):
        result = self.copy()
        result.shrink(padding)
        return result


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


    @_accept_anything_as_vector
    def set_top_left(self, point):
        self.top = point[1]
        self.left = point[0]

    @_accept_anything_as_vector
    def set_top_center(self, point):
        self.top = point[1]
        self.center_x = point[0]

    @_accept_anything_as_vector
    def set_top_right(self, point):
        self.top = point[1]
        self.right = point[0]

    @_accept_anything_as_vector
    def set_center_left(self, point):
        self.center_y = point[1]
        self.left = point[0]

    @_accept_anything_as_vector
    def set_center(self, point):
        self.center_y = point[1]
        self.center_x = point[0]

    @_accept_anything_as_vector
    def set_center_right(self, point):
        self.center_y = point[1]
        self.right = point[0]

    @_accept_anything_as_vector
    def set_bottom_left(self, point):
        self.bottom = point[1]
        self.left = point[0]

    @_accept_anything_as_vector
    def set_bottom_center(self, point):
        self.bottom = point[1]
        self.center_x = point[0]

    @_accept_anything_as_vector
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
    size_as_int = property(get_size_as_int)

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



# Collision Functions

def circle_touching_line(center, radius, start, end):
    """ Return true if the given circle intersects the given segment.  Note 
    that this checks for intersection with a line segment, and not an actual 
    line.

    :param center: Center of the circle.
    :type center: Vector
    :param radius: Radius of the circle.
    :type radius: float
    :param start: The first end of the line segment.
    :type start: Vector
    :param end: The second end of the line segment.
    :type end: Vector
    """

    C, R = center, radius
    A, B = start, end

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


# Mathematical Helper Functions

def clamp(x, low, high):
    """ Forces *x* into the range between *low* and *high*.  In other words, 
    returns *low* if *x* < *low*, returns *high* if *x* > *high*, and returns 
    *x* otherwise. """
    return max(min(x, high), low)


# Exception Classes

class NullVectorError (Exception):
    """ Thrown when an operation chokes on a null vector. """
    pass

class VectorCastError (Exception):
    """ Thrown when an inappropriate object is used as a vector. """

    def __init__(self, object):
        Exception.__init__(self, "Could not cast %s to vector." % type(object))


class RectangleCastError (Exception):
    """ Thrown when an inappropriate object is used as a rectangle. """

    def __init__(self, object):
        Exception.__init__(self, "Could not cast %s to rectangle." % type(object))



