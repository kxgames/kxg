#!/usr/bin/env python

from __future__ import division

# The path module makes it possible to import any of the modules in this
# packages as if they were in this directory.

import sys, path
import random

import pygame
from pygame.locals import *

from shapes import *
from sprites import *

# Setup pygame {{{1
pygame.init()
boundary = Rectangle.from_size(600, 600)
size = boundary.size
screen = pygame.display.set_mode(size)

clock = pygame.time.Clock()
frequency = 40

red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)
cyan = (0,255,255)
purple = (255,0,255)
yellow = (255,255,0)

# Setup the sprites {{{1 
sprites = []
sprite_radius = 10
sprite_force = 75
sprite_speed = 50
population = 25

# Make sprites
for i in range(population):
    sprite_x = boundary.width * random.random()
    sprite_y = boundary.height * random.random()
    sprite_position = Vector(sprite_x,sprite_y)
    sprites.append(Vehicle())
    sprites[i].setup(sprite_position, sprite_radius, sprite_force, sprite_speed)

# Add behaviors to sprites
for i in range(population):
    vehicle = sprites[i]

    wander_radius = sprite_speed * 2
    wander_distance = sprite_speed / 5.0
    wander_jitter = sprite_speed / 2.0
    if 0 == i:
        leader_target = Vehicle()
        leader_target.setup(boundary.center, 1)
        vehicle.add_behavior (Seek (vehicle, 0.4, leader_target))
        vehicle.add_behavior (Wander (vehicle, 1.0, wander_radius, wander_distance, wander_jitter))
    else:
        seek_target = sprites[i-1]
        if 1 == i:
            seek_radius = 0.0
        else:
            seek_radius = sprite_radius * 15
        vehicle.add_behavior (Seek (vehicle, 2.0, seek_target, seek_radius))
        vehicle.add_behavior (Wander (vehicle, 0.9, wander_radius, wander_distance, wander_jitter))

    #flee_target = sprites[i-2]
    #flee_radius = sprite_radius * 10
    #vehicle.add_behavior (Flee (vehicle, 0.8, flee_target, flee_radius))
# }}}1

while True:
    time = clock.tick(frequency) / 1000

    # React to input {{{1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit(0)
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                sys.exit(0)

    # Update the sprites {{{1
    for sprite in sprites:
        sprite.update(time)
        #sprite.bounce(time, boundary)
        sprite.wrap_around(boundary)

    # Draw everything {{{1
    screen.fill((0,0,0))

    # Draw leader target in the center.
    for sprite in sprites:
        leader_position = leader_target.get_position()
        leader_radius = leader_target.get_radius()

        pygame.draw.circle(screen, red, leader_position.pygame, leader_radius)

    # Draw the other sprites.
    for sprite in sprites:
        position = sprite.get_position()
        radius = sprite.get_radius()

        if sprite == sprites[0]:
            pygame.draw.circle(screen, blue, position.pygame, radius, 3)
        else:
            pygame.draw.circle(screen, green, position.pygame, radius, 3)

        # Show which direction the sprite is facing.
        facing = sprite.get_facing()
        end_point = position + facing * 25
        pygame.draw.line(screen, green, position.pygame, end_point.pygame)

        """
        # Draw force lines for the leader
    if True:
        #sum = Vector.null()
        for behavior in sprites[0].get_behaviors():
            force = behavior.get_last_force()
            #sum += force
            if not force == Vector.null():
                #force_start = position + force.normal * sprite_radius
                force_start = sprites[0].get_position()
                force_end = force + force_start
                pygame.draw.line(screen, cyan, force_start.pygame, force_end.pygame)
        """
        """
            # Draw wander circle. Works ONLY if wandering is ONLY behavior
            wander_offset = facing * behavior.d
            wander_radius = behavior.r
            wander_position = wander_offset + position
            pygame.draw.circle(screen, yellow, wander_position.pygame, wander_radius, 1)
            wander_target = behavior.target.get_position() + wander_offset + position
            pygame.draw.circle(screen, red, wander_target.pygame, 5)
            """
        """
        if not sum == Vector.null():
            sum_start = position + sum.normal *sprite_radius
            sum_end = sum + sum_start
            pygame.draw.line(screen, yellow, sum_start.pygame, sum_end.pygame)
        """

    pygame.display.flip()
    # }}}1
