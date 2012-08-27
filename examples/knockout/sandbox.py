#!/usr/bin/env python

import knockout
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('name')
arguments = parser.parse_args()

game = knockout.SandboxLoop(arguments.name)
game.play()
