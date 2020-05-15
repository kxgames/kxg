********************************
Is the KXG Engine Right for You?
********************************
The KXG game engine provides a framework for writing multiplayer games.  To 
help you decide if this engine is appropriate for your game, this page will 
explain how the engine works and what problems it's meant to solve,  list some 
things the engine doesn't do and some libraries you can use to do them, and 
discuss the assumptions and trade-offs that the engine makes.

How the engine works
====================
One of the most difficult parts of writing multiplayer games is making sure 
that all the clients stay in sync with the server, so making this easier is a 
primary focus of the game engine.  The engine approaches this problem by only 
allowing the game state to change if it can ensure that the same change will be 
made to the state of every participating client.  To do this, the engine 
provides a class called :class:`kxg.World` that represents the entire state of 
the game.  The server and each participating client all have their own worlds.  
To keep the worlds in sync, the game engine only allows the world to be 
modified in two ways:

1. The world can update itself.

2. Any player can submit a message to the engine.  The engine will ensure 
   that that message is executed by each participating game.
   
Having the worlds update themselves is safe, because they should be mostly in 
sync to start with.  The worlds can drift out of sync due to slight differences 
in timing and whatnot, but this can be fixed by sending periodic 
synchronization messages.  Having players initiate changes to the worlds is 
potentially more dangerous.  The game engine handles this by requiring you to 
encapsulate these changes in message objects that can be vetted by the server 
and relayed to each participating client.  The game engine also does a lot to 
make sure that:

1. You can't modify the world in an unsafe way.  If you try to, the engine will 
   display a verbose and explanatory message before crashing your game.

2. It's easy to register callbacks for any kind of message from any part of 
   the game that might need to react to one.

3. The objects that make up the game world (called tokens) can be easily and 
   efficiently included in messages.

4. Single-player games are seamlessly supported and that you don't have to 
   write any code that is network-aware.

What the engine doesn't do
==========================
The KXG game engine tries to follow the Unix philosophy of doing one thing only 
and doing that thing well.  The game engine's "thing" is providing a framework 
for keeping multiplayer games in sync, and by extension managing the game loop.  
Anything else that you might need to write a game should be provided by another 
library.  For example, the following features are not part of the game engine:

   - *Graphics:* There are already a number of well-established python graphics 
     libraries for games, and which one you'd use depends on what kind of game 
     you're writing.  The game engine is not a graphics library itself, but 
     it's unobtrusive when it comes to using third-party graphics libraries:

      - ``pyglet`` --- A graphics library based on OpenGL.  Pyglet provides a 
        nice high-level interface to OpenGL, but it also exposes the canonical 
        low-level interface.  The game engine actually depends on pyglet (on 
        its main loop, not its graphics), so it's kind of the default choice.
      
      - ``pygame`` --- A graphics, input, and audio library based on SDL.  
        Pygame is easier to use and more featureful than pyglet, but it's not 
        as fast and only for 2D games.

      - ``glooey`` --- A simple, configurable GUI library for pyglet.
     
   - *Sprites and Steering:* Many games, especially 2D ones, use the concept of 
     sprites.  A sprite is basically a (possibly animated) image that can move 
     around the screen.  Sprites often have steering behavior as well, which 
     keeps them from running into things and allows them to flock.

   - *Math:* There are many python libraries that focus on the kind of maths 
     that games need, like vector arithmetic, collision detection, and graph 
     searching:
     
      - ``vecrec`` --- Full-featured vector and rectangle classes.

      - ``networkx`` --- Path-finding and graph-search algorithms.

Applicable genres of games
==========================
The game engine is relatively agnostic of the kind of game you're trying to 
write, but it's intended for real-time strategy (RTS) games and sometimes this 
intent is to the detriment of other genres.  For example, the game engine uses 
the TCP protocol (which is slower but more reliable than the UDP protocol) to 
send packets over the network.  This is generally a good trade-off for RTS 
games, but it may be too slow for first-person shooter (FPS) games.  The engine 
also keeps the entire world in sync for all the clients, which may be 
impractical for really large role-playing games (RPG).  You could use the 
engine to write a turn-based puzzle-style game, but on one hand the flexibility 
of the game engine's messaging framework would be overkill and on the other 
you'd have to implement all the logic for keeping track of the turn yourself.  
It may be that a simpler library for writing these kinds of game already exists 
(although I am not aware of one).

In general, the game engine is best for games where players can take action at 
any time, but where the exact timing of those actions is not often critical.

