#!/usr/bin/env python3

from .errors import *
from .forums import Forum
from .multiplayer import ClientForum, ServerActor 

class Stage:

    def __init__(self):
        self._successor = None
        self._stop_flag = False

    @property
    def successor(self):
        return self._successor

    @successor.setter
    def successor(self, stage):
        self._successor = stage

    def get_loop(self):
        return self._loop

    def set_loop(self, loop):
        self._loop = loop

    def exit_stage(self):
        """ Stop this stage from executing once the current update ends. """
        self._stop_flag = True

    def exit_program(self):
        """ Exit the game once the current update ends. """
        self._loop.exit()

    def is_finished(self):
        """ Return true if this stage is done executing. """
        return self._stop_flag

    def get_successor(self):
        """ Create and return the stage that should be executed next. """
        return None

    def on_enter_stage(self):
        raise NotImplementedError

    def on_update_stage(self, dt):
        raise NotImplementedError

    def on_exit_stage(self):
        raise NotImplementedError


class GameStage (Stage):

    def __init__(self, world, forum, actors):
        Stage.__init__(self)

        from .world import require_world
        from .forums import require_forum
        from .actors import require_actors

        require_world(world)
        require_forum(forum)
        require_actors(actors)

        self.world = world
        self.forum = forum
        self.actors = actors
        self.successor = None

    def on_enter_stage(self):
        """
        Prepare the actors, the world, and the messaging system to begin 
        playing the game.
        
        This method is guaranteed to be called exactly once upon entering the 
        game stage.
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

        for actor in self.actors:
            actor.on_start_game()

    def on_update_stage(self, dt):
        """
        Sequentially update the actors, the world, and the messaging system.  
        The loop terminates once all of the actors indicate that they are done.
        """

        for actor in self.actors:
            actor.on_update_game(dt)

        self.forum.on_update_game()

        with self.world._unlock_temporarily():
            self.world.on_update_game(dt)

        if self.world.is_game_over():
            self.exit_stage()

    def on_exit_stage(self):
        """
        Give the actors, the world, and the messaging system a chance to react 
        to the end of the game.
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

    def get_successor(self):
        """
        Return the stage that will be run by the loop after this one finishes.
        """
        return self.successor

    def set_successor(self, successor):
        """
        Set the stage that will be run by the loop after this one finishes.
        """
        self.successor = successor


class UniplayerGameStage (GameStage):

    def __init__(self, world, referee, other_actors):
        forum = Forum()
        actors = [referee] + other_actors
        GameStage.__init__(self, world, forum, actors)


class MultiplayerClientGameStage (Stage):

    def __init__(self, world, actor, pipe):
        super().__init__()
        self.world = world
        self.actor = actor
        self.forum = ClientForum(pipe)

    def on_enter_stage(self):
        pass

    def on_update_stage(self, dt):
        if self.forum.receive_id_from_server():
            self.exit_stage()

    def on_exit_stage(self):
        pass

    def get_successor(self):
        return GameStage(self.world, self.forum, [self.actor])


class MultiplayerServerGameStage (GameStage):

    def __init__(self, world, referee, pipes):
        forum = Forum()
        actors = [referee] + [ServerActor(x) for x in pipes]
        GameStage.__init__(self, world, forum, actors)




