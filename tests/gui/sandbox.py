#!/usr/bin/env python

import path
import kxg
import pyglet
import random

background = kxg.gui.blue
foreground = (
        kxg.gui.red, kxg.gui.brown, kxg.gui.orange,
        kxg.gui.yellow, kxg.gui.green, kxg.gui.purple,
)

window = pyglet.window.Window()
#window.set_fullscreen(True)
batch = pyglet.graphics.Batch()
gui = kxg.gui.Window(window)

#gui.connect('mouse-push', kxg.tools.echo)

fill = kxg.gui.Rectangle(background)
gui.fill(fill)

grid = kxg.gui.Grid(3, 3, padding=20)
gui.add(grid)

for x in range(3):
    for y in range(3):
        color = random.choice(foreground)
        cell = kxg.gui.Rectangle(color)
        grid.add(cell, y, x)

@window.event
def on_draw():
    window.clear()
    gui.draw(batch)
    batch.draw()

pyglet.app.run()

