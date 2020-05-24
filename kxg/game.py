#!/usr/bin/env python3

from .errors import *
from .forums import Forum
from .multiplayer import ClientForum, ServerActor

class Game:

    def __init__(self, world, forum, actors):
        # Allow the actors argument to be a generator.
        actors = list(actors)

        from .tokens import require_world; require_world(world)
        from .forums import require_forum; require_forum(forum)
        from .actors import require_actors; require_actors(actors)

        self.world = world
        self.forum = forum
        self.actors = actors

    def start_game(self):
        """
        Prepare the actors, the world, and the messaging system to begin 
        playing the game.

        This method should be called exactly once by every host and client 
        involved in the game.
        """
        with self.world._unlock_temporarily():
            self.forum.connect_everyone(self.world, self.actors)

        # 1. Setup the forum.

        self.forum.on_start_game()

        # 2. Setup the world.

        with self.world._unlock_temporarily():
            self.world.on_start_game()

        # 3. Setup the actors.  Because this is done after the forum and the  
        #    world have been setup, this signals to the actors that they can 
        #    send messages and query the game world as usual.

        num_players = len(self.actors) - 1

        for actor in self.actors:
            actor.on_start_game(num_players)

    def update_game(self, elapsed_time):
        """
        Sequentially update the actors, the world, and the messaging system.  

        This method should be called every frame by every host and client 
        involved in the game.
        """

        for actor in self.actors:
            actor.on_update_game(elapsed_time)

        self.forum.on_update_game()

        with self.world._unlock_temporarily():
            self.world.on_update_game(elapsed_time)

    def finish_game(self):
        """
        Give the actors, the world, and the messaging system a chance to react 
        to the end of the game.

        This method should be called exactly once by every host and client 
        involved in the game.
        """

        # 1. Let the forum react to the end of the game.  Local forums don't 
        #    react to this, but remote forums take the opportunity to stop 
        #    trying to extract tokens from messages.

        self.forum.on_finish_game()

        # 2. Let the actors react to the end of the game.

        for actor in self.actors:
            actor.on_finish_game()

        # 3. Let the world react to the end of the game.

        with self.world._unlock_temporarily():
            self.world.on_finish_game()


class UniplayerGame(Game):

    def __init__(self, world, referee, gui_actor, ai_actors=None):
        forum = Forum()
        actors = [referee, gui_actor] + list(ai_actors or [])
        super().__init__(world, forum, actors)


class MultiplayerClientGame(Game):

    def __init__(self, world, gui_actor, pipe):
        forum = ClientForum(pipe)
        super().__init__(world, forum, [gui_actor])


class MultiplayerServerGame(Game):

    def __init__(self, world, referee, ai_actors, pipes):
        forum = Forum()
        actors = [referee] + [ServerActor(x) for x in pipes] + ai_actors
        super().__init__(world, forum, actors)




