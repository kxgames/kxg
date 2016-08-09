***************
Common Mistakes
***************

1. Modifying a token directly from an actor.

   Caught by the safety checks.

2. Adding the same token to the world twice.

   Caught during message sending.

3. Removing the same token from the world twice.

   Caught during message sending.

4. Adding a token to the world without sending a message, e.g.  
   world.sprockets.append(Sprocket())

   Caught during message pickling (multiplayer only).  This isn't a perfect 
   solution, because the error will come long after the actual mistake (which 
   the error message should make clear).  You can also put tokens in the world 
   and then just never reference them in messages, but I guess "if a tree falls 
   in the woods"...

5. Using a token that's been removed from the world.  This could happen if you 
   remove a token, but accidentally leave some stale references to it.

   Caught during message pickling (multiplayer only).  

How is 5 different than 4?  



The message pickling step seems like a pretty good place to check for token 
usage mistakes.  It's a place where token participation in the world is being 
set and where I know what everything should be.


