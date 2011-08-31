from vector import *
from shapes import *

class Sprite:
    """ A parent class for every game object that can move.  This class stores
    position data and handles basic physics, but it is not meant to be
    directly instantiated. """
    # Constructor {{{1

    def __init__(self):
        self.circle = None
        self.behaviors = []
        self.facing = Vector.random()

        self.velocity = Vector.null()
        self.acceleration = Vector.null()
        self.behavior_acceleration = Vector.null()

    def setup(self, position, radius, force=0.0, speed=0.0, facing=Vector.null()):
        self.circle = Circle(position, radius)
        self.force = force
        self.speed = speed
        if not facing == Vector.null():
            self.facing = facing.normal

    # Updates {{{1
    def update(self, time):
        acceleration = self.acceleration
        # Calculate change to acceleration. Accounts for the weight and
        # prioritization of each behavior. For these purposes, force and
        # acceleration are basically the same in name.
        remaining_force = self.force
        for behavior in self.behaviors:
            ideal_force, weight = behavior.update()
            force = ideal_force * weight
            if force.magnitude <= remaining_force:
                remaining_force -= force.magnitude
                acceleration += force
            elif remaining_force > 0:
                final_force = force.normal * remaining_force
                acceleration += final_force
                break
            else:
                break

        # This is the "Velocity Verlet Algorithm".  I learned it in my
        # computational chemistry class, and it's a better way to integrate
        # Newton's equations of motions than what we were doing before.
        self.velocity += acceleration * (time / 2)
        self.check_velocity()
        self.circle = Circle.move(self.circle, self.velocity * time)
        self.velocity += acceleration * (time / 2)
        self.check_velocity()

        if self.velocity.magnitude > 0.00001:
            self.facing = self.velocity.normal

        self.behavior_acceleration = acceleration

    def bounce(self, time, boundary):
        x, y = self.circle.center
        vx, vy = self.velocity

        bounce = False

        # Check for collisions against the walls.
        if y < boundary.top or y > boundary.bottom:
            bounce = True
            vy = -vy

        if x < boundary.left or x > boundary.right:
            bounce = True
            vx = -vx

        # If there is a bounce, flip the velocity and move back onto the
        # screen.
        if bounce:
            self.velocity = Vector(vx, vy)
            self.circle = Circle.move(self.circle, self.velocity * time)

    def wrap_around(self, boundary):
        x, y = self.circle.center

        x = x % boundary.width
        y = y % boundary.height

        position = Vector(x, y)
        self.circle = Circle(position, self.circle.radius)

    # Methods {{{1
    def check_velocity(self):
        if self.velocity.magnitude > self.speed:
            self.velocity = self.velocity.normal * self.speed
    def add_behavior(self, behavior):
        self.behaviors.append(behavior)

    # Attributes {{{1
    def get_position(self):
        return self.circle.center

    def set_position(self, position):
        self.circle = Circle.move(self.circle, position - self.circle.center)

    def get_velocity(self):
        return self.velocity

    def get_acceleration(self):
        return self.acceleration

    def get_radius(self):
        return self.circle.radius

    def get_circle(self):
        return self.circle
    
    def get_speed(self):
        return self.speed

    def get_behaviors(self):
        return self.behaviors

    def get_facing(self):
        return self.facing
    
    def set_position(self, position):
        radius = self.circle.get_radius()
        self.circle = Circle(position, radius)

    def get_behavior_acceleration(self):
        return self.behavior_acceleration
    # }}}1

class Base:
    # The Base class for all behavior classes.
    # Base {{{1
    def __init__ (self, sprite, weight):
        self.sprite = sprite
        self.weight = weight
        self.last_force = Vector.null()

    def get_last_force(self):
        return self.last_force
    # }}}1

class Seek(Base):
    # Seek {{{1
    def __init__ (self, sprite, weight, target, los=0.0):
        Base.__init__(self, sprite, weight)

        self.target = target
        self.los = los

    def update (self):
        desired_direction = self.target.get_position() - self.sprite.get_position()
        if 0.0 == self.los or desired_direction.magnitude <= self.los:
            desired_normal = desired_direction.normal
            desired_velocity = desired_normal * self.sprite.get_speed()
            force = desired_velocity - self.sprite.get_velocity()
        else:
            force = Vector.null()

        # Returns a force, not velocity. Velocities are used in these
        # calculations to find delta_velocity. delta_velocity = acceleration *
        # time. The time step will be dealt with later and, for our purposes,
        # acceleration is basically the same as force. 
        self.last_force = force
        return force, self.weight
    # }}}1

class Flee(Base):
    # Flee {{{1
    def __init__ (self, sprite, weight, target, los=0.0):
        Base.__init__(self, sprite, weight)

        self.target = target
        self.los = los

    def update (self):
        desired_direction = self.sprite.get_position() - self.target.get_position()
        if 0.0 == self.los or desired_direction.magnitude <= self.los:
            try:
                desired_normal = desired_direction.normal
            except NullVectorError:
                desired_normal = Vector.null()
            desired_velocity = desired_normal * self.sprite.get_speed()
            force = desired_velocity - self.sprite.get_velocity()
        else:
            force = Vector.null()

        # Returns a force, not velocity. Velocities are used in these
        # calculations to find delta_velocity. delta_velocity = acceleration *
        # time. The time step will be dealt with later and, for our purposes,
        # acceleration is basically the same as force. 
        self.last_force = force
        return force, self.weight
    # }}}1

class Wander(Base):
    # Wander {{{1
    def __init__ (self, sprite, weight, radius, distance, jitter):
        Base.__init__(self, sprite, weight)

        self.target = Sprite()
        #self.seek_target = Sprite()
        #self.seek = Seek(sprite, weight, self.seek_target)

        self.r = radius
        self.d = distance
        self.j = jitter

        circle_position = Vector.random() * radius
        self.target.setup(circle_position, 1)

        #self.seek_target.setup(circle_position, 1)

    def update(self):
        circle_position = self.target.get_position()

        jitter = Vector.random() * self.j
        wander_position = circle_position + jitter
        new_circle_position = wander_position.normal * self.r

        self.target.set_position(new_circle_position)

        facing_offset = self.sprite.get_facing() * self.d
        relative_position = new_circle_position + facing_offset
        
        #self.seek_target.set_position(relative_position)

        self.last_force = relative_position
        #return self.seek.update()
        return relative_position, self.weight
    # }}}1

