Overview
========
Knockout is a simple console-based game meant to test the KXG multiplayer game
engine.  Because the game engine was designed for real-time strategy games,
this game is intended to represent that genre while remaining extremely simple.

The game is played between two players.  Players can press <enter> to attack
each other, and the first player to go below zero health loses.  The strength
of each attack depends on how much time elapsed since the last attack.  

Because players can attack at any time, the game is real-time.  Because players
must consider the trade-offs between attacking quickly and attacking slowly,
the game also has strategy.  Information only has to be exchanged between
clients when someone makes a move, which is similar to how the network would be
used in a more full-fledged game.
