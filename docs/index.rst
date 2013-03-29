KXG Game Engine Documentation
=============================
This library is intended to facilitate the development of reasonably 
sophisticated computer games.  Towards that ends, it provided components for 
building graphical interfaces, manipulating moving sprites, performing vector 
calculations, passing messages across the network, and updating the game loop.  
These components were designed to allow both the rapid assembly of prototype 
games and the painless conversion of those prototypes into full-fledged 
games.

The library can be downloaded from one of two git repositories.  The first 
repository has can be pushed to, but requires a key on the KXG server.  Your 
SSH configuration must also contain the appropriate definition of the `kxgames` 
host.  The second repository is read-only and available to anyone.  

.. code-block:: bash
    
    git clone kxgames:git/engine/code
    git clone git://kxgames.net/engine/code

Note that although the API is functional in many ways, it is not stable.  Until 
the API stabilizes, the project version number will remain 0.1 and you should 
test your code carefully after pulling a new version of the library.

.. toctree::
    :maxdepth: 2
    :numbered:

    engine.rst
    geometry.rst
    gui.rst
    messaging.rst
    network.rst
    sprites.rst
    tools.rst
