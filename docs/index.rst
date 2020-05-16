***************
KXG Game Engine
***************
This library provides a framework for writing multiplayer computer games.  The 
game engine is easy to use, requires almost no boilerplate code, and scales 
painlessly from prototypes to full-fledged games.  The engine is driven by a 
message passing framework that was designed to be intuitive and optimized to 
avoid lag.  The game engine is also very good at noticing when it's being 
misused and explaining how it should be used with detailed error messages.  
This makes it easier to start using the engine and harder to make subtle 
synchronization bugs that would otherwise be very difficult to track down.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   right_for_you
   installation
   demos/guess_my_number

.. toctree::
   :caption: Learning More

   big_picture.rst
   messaging_overview.rst
   theater_overview.rst
   token_overview.rst
   common_mistakes.rst

.. autosummary::
   :caption: API Reference
   :toctree: api
   :recursive:

   kxg.tokens
   kxg.messages
   kxg.actors
   kxg.forums
   kxg.multiplayer
   kxg.quickstart
   kxg.errors

.. toctree::
   :caption: Miscellaneous

   contributing.rst

