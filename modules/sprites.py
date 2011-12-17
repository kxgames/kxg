from vector import *
from utilities.infinity import *

class Sprite:
    """ A parent class for every game object that can move.  This class stores
    position data and handles basic physics, but it is not meant to be
    directly instantiated. """

    # Constructor {{{1
    def __init__(self):
        self.position = Vector.null()
        self.velocity = Vector.null()
        self.acceleration = Vector.null()

        self.max_acceleration = infinity
        self.max_velocity = infinity

    def setup(self, r=Vector.null(), max_a=infinity, max_v=infinity):
        self.position = r
        self.max_acceleration = max_a
        self.max_velocity = max_v

    # Updates {{{1
    def update(self, time):
        self.check_acceleration()
        self.check_velocity()

        # This is the "Velocity Verlet" algorithm.  I learned it in my
        # computational chemistry class, and it's a better way to integrate
        # Newton's equations of motion than what we were doing before.

        self.velocity += self.acceleration * (time / 2); self.check_velocity()
        self.position += self.velocity * time
        self.velocity += self.acceleration * (time / 2); self.check_velocity()

    def check_acceleration(self):
        a = self.acceleration
        if a.magnitude > self.max_acceleration:
            self.acceleration = a.normal * self.max_acceleration

    def check_velocity(self):
        if self.velocity.magnitude > self.max_velocity:
            self.velocity = self.velocity.normal * self.max_velocity

    # Attributes {{{1
    def get_position(self):
        return self.position

    def get_velocity(self):
        return self.velocity

    def get_acceleration(self):
        return self.acceleration

    def get_max_velocity(self):
        return self.max_acceleration

    def get_max_acceleration(self):
        return self.max_acceleration

    def set_position(self, position):
        self.position = position

    def set_velocity(self, velocity):
        self.velocity = velocity
        self.check_velocity()

    def set_acceleration(self, acceleration):
        self.acceleration = acceleration
        self.check_acceleration()

    def get_max_velocity(self):
        return self.max_acceleration

    def get_max_acceleration(self):
        return self.max_acceleration

    # }}}1

class Vehicle (Sprite):
    """ An application of the Sprite class with flocking capabilities. 
    Note: Non-behavior (ie: external) accelerations are ignored."""

    # Constructor {{{1

    def __init__(self):
        Sprite.__init__ (self)

        self.behaviors = []

        self.facing = Vector.random()
        self.mass = 1
        self.behavior_acceleration = Vector.null()

    def setup(self, pos, mass=1, max_a=inf, max_v=inf, facing=Vector.null()):
        Sprite.setup(self, pos, max_a, max_v)
        self.mass = mass
        if not facing == Vector.null():
            self.facing = facing.normal

    # Updates {{{1
    def update(self, time):
        """ Update acceleration. Accounts for the importance and
        priority (order) of multiple behaviors. """
        total_acceleration = Vector.null()
        max_jerk = self.max_acceleration

        for behavior in self.behaviors:
            acceleration, importance = behavior.update()
            weighted_acceleration = acceleration * importance

            if max_jerk >= weighted_acceleration.magnitude:
                max_jerk -= weighted_acceleration.magnitude
                total_acceleration += weighted_acceleration
            elif max_jerk > 0 and max_jerk < weighted_acceleration.magnitude:
                total_acceleration += weighted_acceleration.normal * max_jerk
                break
            else:
                break

        self.acceleration = total_acceleration

        # Update position and velocity.
        Sprite.update(self, time)

        # Update facing direction.
        if self.velocity.magnitude > 0.0:
            self.facing = self.velocity.normal

    # Methods {{{1
    def add_behavior(self, behavior):
        self.behaviors.append(behavior)

    # Attributes {{{1
    def get_behaviors(self):
        return self.behaviors

    def get_facing(self):
        return self.facing

    # }}}1

class Base:
    """ The base class for all behavior classes. """
    # Base {{{1
    def __init__ (self, sprite, weight):
        self.sprite = sprite
        self.weight = weight
        self.last_delta_velocity = Vector.null()

    def get_delta_velocity (self):
        return self.last_delta_velocity
    # }}}1

class Seek(Base):
    # Seek {{{1
    def __init__ (self, sprite, weight, target, los=0.0):
        Base.__init__(self, sprite, weight)

        self.target = target
        self.los = los

    def update (self):
        """ Calculate what the desired change in velocity is. 
        delta_velocity = acceleration * delta_time
        Time will be dealt with by the sprite. """
        delta_velocity = Vector.null()
        target_position = self.target.get_position()
        sprite_position = self.sprite.get_position()

        desired_direction = target_position - sprite_position

        if 0.0 == self.los or desired_direction.magnitude <= self.los:
            desired_normal = desired_direction.normal
            desired_velocity = desired_normal * self.sprite.get_max_speed()
            delta_velocity = desired_velocity - self.sprite.get_velocity()

        self.last_delta_velocity = delta_velocity
        return delta_velocity, self.weight
    # }}}1

class Flee(Base):
    # Flee {{{1
    def __init__ (self, sprite, weight, target, los=0.0):
        Base.__init__(self, sprite, weight)

        self.target = target
        self.los = los

    def update (self):
        """ Calculate what the desired change in velocity is. 
        delta_velocity = acceleration * delta_time
        Time will be dealt with by the sprite. """
        delta_velocity = Vector.null()
        target_position = self.target.get_position()
        sprite_position = self.sprite.get_position()

        desired_direction = target_position - sprite_position

        if 0.0 == self.los or desired_direction.magnitude <= self.los:
            try:
                desired_normal = desired_direction.normal
            except NullVectorError:
                desired_normal = Vector.null()
            desired_velocity = desired_normal * self.sprite.get_max_speed()
            delta_velocity = desired_velocity - self.sprite.get_velocity()

        self.last_delta_velocity = delta_velocity
        return delta_velocity, self.weight
    # }}}1

class Wander(Base):
    # Wander {{{1
    def __init__ (self, sprite, weight, wander_radius, distance, jitter):
        Base.__init__(self, sprite, weight)

        self.target = Sprite()

        self.r = wander_radius
        self.d = distance
        self.j = jitter

        position = Vector.random() * wander_radius
        self.target.setup(position)

    def update(self):
        position = self.target.get_position()

        jitter = Vector.random() * self.j
        jittered_position = position + jitter
        new_target_position = wander_position.normal * self.r

        self.target.set_position(new_target_position)

        facing_offset = self.sprite.get_facing() * self.d
        desired_position = new_target_position + facing_offset
        
        desired_velocity = desired_position
        delta_velocity = desired_velocity.normal * self.sprite.get_max_speed()

        # Try to reduce slowing down effect when multiple behaviors are 
        # in effect? Dont know if this is actually a problem.

        self.last_delta_velocity = delta_velocity
        return delta_velocity, self.weight
    # }}}1

