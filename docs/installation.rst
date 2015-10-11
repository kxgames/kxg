*************************
Installing the KXG Engine
*************************
The library is distributed under the `MIT license 
<https://en.wikipedia.org/wiki/Comparison_of_free_and_open-source_software_licenses>`_, 
so it can be used for both open and closed source games, but modifications to 
the engine itself must be made open source.  You can install the library using 
pip:

.. code-block:: bash

    pip install kxg

You can also install the library by `downloading the source code from GitHub 
<https://github.com/kxgames/kxg>`_ and manually running the ``setup.py`` 
script:

.. code-block:: bash
    
    git clone git@github.com:kxgames/kxg.git
    python3 kxg/setup.py install

We recommend making a new virtual environment for each game you write.  The 
process of making a virtual environment and installing the game engine would 
look something like this:

.. code-block:: bash

    mkdir my_game
    cd my_game
    virtualenv -p python3 env
    ./env/bin/pip install kxg

Dependencies
============
The kxg game engine depends on a handful of libraries and works seamlessly with 
libraries that facilitate different aspects of writing games.  The engine's 
biggest dependency is python 3.  It also requires the following libraries:

   - ``pyglet`` --- A powerful OpenGL API.  The game engine makes use of 
     pyglet's main loop, which is quite full-featured.

   - ``linersock`` --- Convenient wrappers around bare sockets that the game 
     engine uses to communicate over the network.

   - ``nonstdlib`` --- A collection of short and generally useful utilities.

   - ``pytest`` --- An easy-to-use and easy-to-debug-with unit testing 
     framework.  Only needed if you want to run the unit tests.

All of these libraries will be installed automatically by either ``pip`` or the 
``setup.py`` script.

