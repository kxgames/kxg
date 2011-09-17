from __future__ import division

from math import *
from vector import Vector

class Shape(object):

    # Constructor {{{1
    def __init__(self, position):
        self.__position = position

        self.__inside = {}
        self.__outside = {}

    # Attributes {{{1
    def get_position(self): return self.__position
    def get_horizontal(self): return self.__position.x
    def get_vertical(self): return self.__position.y

    def get_left(self): raise NotImplementedError
    def get_right(self): raise NotImplementedError
    def get_top(self): raise NotImplementedError
    def get_bottom(self): raise NotImplementedError

    def set_position(self, new_position):
        allow_move = True 

        old_position = self.__position
        self.__position = new_position

        for shape, callback in self.__inside.items():
            inside = violations = self.inside(shape)
            if not inside: allow_move = callback(*violations) and allow_move

        for shape, callback in self.__outside.items():
            outside = violations = self.outside(shape)
            if not outside: allow_move = callback(*violations) and allow_move

        self.__position = new_position if allow_move else old_position

    def set_horizontal(self, horizontal):
        position = Vector(horizontal, self.vertical)
        self.set_position(position)

    def set_vertical(self, vertical):
        position = Vector(self.horizontal, vertical)
        self.set_position(position)

    def set_left(self, left):
        difference = left - self.get_left()
        displacement = Vector(difference, 0)

        self.displace(displacement)

    def set_right(self, right):
        difference = right - self.get_right()
        displacement = Vector(difference, 0)

        self.displace(displacement)

    def set_top(self, top):
        difference = top - self.get_top()
        displacement = Vector(0, difference)

        self.displace(displacement)

    def set_bottom(self, bottom):
        difference = bottom - self.get_bottom()
        displacement = Vector(0, difference)

        self.displace(displacement)

    position = property(get_position, set_position)
    horizontal = property(get_horizontal, set_horizontal)
    vertical = property(get_vertical, set_vertical)

    # }}}1

    # Copy Method {{{1
    def copy(self):
        from copy import deepcopy
        return deepcopy(self)

    # Movement Methods {{{1
    def displace(self, displacement):
        position = self.get_position() + displacement
        self.set_position(position)

    def reposition(self, position):
        self.set_position(position)

    def align_left(self, other):
        target = other.get_left()
        self.set_left(target)

    def align_right(self, other):
        target = other.get_right()
        self.set_right(target)

    def align_top(self, other):
        target = other.get_top()
        self.set_top(target)

    def align_bottom(self, other):
        target = other.get_bottom()
        self.set_bottom(target)

    def align_horizontal(self, other):
        target = other.get_horizontal()
        self.set_horizontal(target)

    def align_vertical(self, other):
        target = other.get_vertical()
        self.set_vertical(target)

    # Collision Methods {{{1
    def inside(self, shape):
        top_out = self.get_top() < shape.get_top()
        bottom_out = self.get_bottom() > shape.get_bottom()

        left_out = self.get_left() < shape.get_left()
        right_out = self.get_right() > shape.get_right()

        return Violations(top_out, left_out, bottom_out, right_out)

    def outside(self, shape):
        top_in = self.get_top() < shape.get_bottom()
        bottom_in = self.get_bottom() > shape.get_top()

        left_in = self.get_left() < shape.get_right()
        right_in = self.get_right() > shape.get_left()

        inside = top_in and left_in and bottom_in and right_in

        if not inside:
            return Violations(False, False, False, False)

        top_out = self.get_top() < shape.get_top()
        bottom_out = self.get_bottom() > shape.get_bottom()

        left_out = self.get_left() < shape.get_left()
        right_out = self.get_right() > shape.get_right()

        return Violations(bottom_out, right_out, top_out, left_out)

    def keep_inside(self, shape, callback=lambda t,l,b,r: False):
        self.__inside[shape] = callback

    def keep_outside(self, shape, callback=lambda t,l,b,r: False):
        self.__outside[shape] = callback

    # }}}1

class Point(Shape):

    # Constructor {{{1
    def __init__(self, *arguments):
        if len(arguments) == 1:
            position = arguments[0]
        elif len(arguments) == 2:
            position = Vector(*arguments)
        else:
            message = "Point() takes either one or two arguments. %d given."
            raise ValueError(message % len(messages))

        Shape.__init__(self, position)

    def __eq__(self, other):
        return self.position == other.position

    def __repr__(self):
        return "Point: %s" % self.position

    # Attributes {{{1
    get_x = Shape.get_horizontal; get_y = Shape.get_vertical
    set_x = Shape.set_horizontal; set_y = Shape.set_vertical

    x = property(get_x, set_x)
    y = property(get_y, set_y)

    def get_left(self): return self.x
    def get_right(self): return self.x
    def get_top(self): return self.y
    def get_bottom(self): return self.y

    left = property(get_left, Shape.set_left)
    right = property(get_right,  Shape.set_right)
    top = property(get_top,  Shape.set_top)
    bottom = property(get_bottom,  Shape.set_bottom)

    # }}}1

class Line(Shape):

    # Constructor {{{1
    def __init__(self, head, tail):
        position = (head + tail) / 2
        direction = head - position

        Shape.__init__(self, position)
        self.__direction = direction

    def __eq__(self, other):
        first, second = self.points
        if (first, second) == other.points: return True
        if (second, first) == other.points: return True
        return False

    def __repr__(self):
        return "Line: %s to %s" % (self.tail, self.head)

    # Attributes {{{1
    def get_head(self): return self.position + self.__direction
    def get_tail(self): return self.position - self.__direction

    def get_points(self): return self.head, self.tail
    def get_pygame(self): return self.head.pygame, self.tail.pygame

    def set_head(self, head):
        displacement = head - self.head
        self.displace(displacement)

    def set_tail(self, tail):
        displacement = tail - self.tail
        self.displace(displacement)

    def set_points(self, head, tail):
        self.head = head
        self.tail = tail

    def get_left(self): return self.position.x - abs(self.__direction.x)
    def get_right(self): return self.position.x + abs(self.__direction.x)
    def get_top(self): return self.position.y - abs(self.__direction.y)
    def get_bottom(self): return self.position.y + abs(self.__direction.y)

    head = property(get_head, set_head)
    tail = property(get_tail, set_tail)

    points = property(get_points, set_points)
    pygame = property(get_pygame)

    left = property(get_left, Shape.set_left)
    right = property(get_right,  Shape.set_right)
    top = property(get_top,  Shape.set_top)
    bottom = property(get_bottom,  Shape.set_bottom)

    # Factory Methods {{{1
    @staticmethod
    def from_width(width):
        head = Vector(0, 0); tail = Vector(width, 0)
        return Line(head, tail)

    @staticmethod
    def from_height(height):
        head = Vector(0, 0); tail = Vector(0, height)
        return Line(head, tail)

    # }}}1

class Circle(Shape):

    # Constructor {{{1
    def __init__(self, position, radius):
        Shape.__init__(self, position)
        self.__radius = radius

    def __eq__(self, other):
        return self.position == other.position and self.radius == other.radius

    def __repr__(self):
        return "Circle: %s, r=%d" % (self.position, self.radius)

    # Attributes {{{1
    def get_radius(self): return self.__radius
    def get_diameter(self): return 2 * self.__radius

    def set_radius(self, radius): self.__radius = radius
    def set_diameter(self, diameter): self.__radius = diameter / 2

    def get_pygame(self): return self.position.pygame, int(self.radius)

    def get_left(self): return self.horizontal - self.radius
    def get_right(self): return self.horizontal + self.radius
    def get_top(self): return self.vertical - self.radius
    def get_bottom(self): return self.vertical + self.radius

    radius = property(get_radius, set_radius)
    diameter = property(get_diameter, set_diameter)

    pygame = property(get_pygame)

    left = property(get_left, Shape.set_left)
    right = property(get_right,  Shape.set_right)
    top = property(get_top,  Shape.set_top)
    bottom = property(get_bottom,  Shape.set_bottom)

    # Factory Methods {{{1
    @staticmethod
    def from_radius(radius):
        position = Vector.null()
        return Circle(position, radius)

    @staticmethod
    def from_diameter(diameter):
        position = Vector.null()
        return Circle(position, diameter / 2)

    @staticmethod
    def from_dimensions(position, radius):
        return Circle(position, radius)

    # }}}1

class Rectangle(Shape):

    # Constructor {{{1
    def __init__(self, position, width, height):
        Shape.__init__(self, position)
        self.__width = width; self.__height = height

    def __eq__(self, other):
        return ( self.top == other.top and self.bottom == other.bottom and
                 self.left == other.left and self.right == other.right )

    def __repr__(self):
        dimensions = self.position, self.width, self.height
        return "Rectangle: %s, %dx%d" % dimensions

    # Attributes {{{1
    def get_width(self): return self.__width
    def get_height(self): return self.__height
    def get_size(self): return self.__width, self.__height

    def get_dimensions(self):
        return self.left, self.top, self.width, self.height

    def get_pygame(self):
        from pygame.rect import Rect
        return Rect(self.left, self.top, self.width, self.height)

    def set_width(self, width): self.__width = width
    def set_height(self, height): self.__height = height
    def set_size(self, width, height):
        self.__width, self.__height = width, height

    def get_left(self): return self.horizontal - self.width / 2
    def get_right(self): return self.horizontal + self.width / 2
    def get_top(self): return self.vertical - self.height / 2
    def get_bottom(self): return self.vertical + self.height / 2

    golden_ratio = 1/2 + sqrt(5) / 2

    width = property(get_width, set_width)
    height = property(get_height, set_height)
    size = property(get_size, set_size)

    dimensions = property(get_dimensions)
    pygame = property(get_pygame)

    left = property(get_left, Shape.set_left)
    right = property(get_right, Shape.set_right)
    top = property(get_top, Shape.set_top)
    bottom = property(get_bottom, Shape.set_bottom)

    # Factory Methods {{{1
    @staticmethod
    def from_size(width, height):
        position = Vector(width, height) / 2
        return Rectangle(position, width, height)

    @staticmethod
    def from_width(width, ratio=1/golden_ratio):
        height = ratio * width
        return Rectangle.from_size(width, height)

    @staticmethod
    def from_height(height, ratio=golden_ratio):
        width = ratio * height
        return Rectangle.from_size(width, height)

    @staticmethod
    def from_dimensions(left, top, width, height):
        horizontal = left + (width / 2)
        vertical = top + (height / 2)

        position = Vector(horizontal, vertical)
        return Rectangle(position, width, height)

    @staticmethod
    def from_sides(left, top, right, bottom):
        width = right - left
        height = bottom - right

        return Rectangle.from_dimensions(left, right, width, height)

    @staticmethod
    def from_center(position, width, height):
        return Rectangle(position, width, height)

    @staticmethod
    def from_circle(circle):
        position = circle.position
        diameter = circle.diameter

        return Rectangle(position, diameter, diameter)

    @staticmethod
    def from_union(self, first, second):
        right = max(first.right, second.right)
        bottom = min(first.bottom, second.bottom)

        left = max(first.left, second.left)
        right = min(first.right, second.right)

        return Rectangle.from_sides(left, right, right, bottom)

    # }}}1

class Violations:

    # Constructor {{{1
    def __init__(self, top, left, bottom, right):
        self.violations = top, left, bottom, right

    # Operators {{{1 
    def __iter__(self):
        return iter(self.violations)

    def __nonzero__(self):
        return not any(self.violations)

    def __repr__(self):
        return str(bool(self))
    # }}}1

if __name__ == "__main__":

    import pygame
    from pygame import *

    pygame.init()

    window = Rectangle.from_width(500)
    field = Rectangle.from_width(400)

    player = Rectangle.from_size(5, 50)
    opponent = Rectangle.from_size(5, 50)

    size = int(window.width), int(window.height)
    screen = pygame.display.set_mode(size)

    black = 0, 0, 0
    white = 255, 255, 255

    red = 255, 0, 0
    green = 0, 255, 0
    blue = 0, 0, 255

    colors = black, red, green, blue
    rectangles = field, player, opponent

    field.align_horizontal(window)
    field.align_vertical(window)

    player.align_left(field)
    player.align_vertical(field)

    opponent.align_right(field)
    opponent.align_vertical(field)

    screen.fill(white)

    while True:

        for index, rectangle in enumerate(rectangles):
            color = colors[index % len(colors)]
            dimensions = rectangle.pygame

            pygame.draw.rect(screen, color, dimensions, 1)

        pygame.display.flip()
        pygame.time.wait(50)
