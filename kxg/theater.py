#!/usr/bin/env python3

import pyglet
from .errors import *
from .forums import Forum
from .multiplayer import ClientForum, ServerActor 

class Theater:
    """
    Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages.
    """

    def __init__(self, initial_stage=None):
        self._initial_stage = initial_stage
        self._current_stage = None

    @property
    def initial_stage(self):
        return self._initial_stage

    @initial_stage.setter
    def initial_stage(self, stage):
        if self._current_stage:
            raise TheaterAlreadyPlaying()
        self._initial_stage = stage

    @property
    def current_stage(self):
        return self._current_stage

    def update(self, dt):
        if not self._current_stage:
            self._current_stage = self._initial_stage
            self._current_stage.theater = self
            self._current_stage.on_enter_stage()

        self._current_stage.on_update_stage(dt)

        if self._current_stage.is_finished:
            self._current_stage.on_exit_stage()
            self._current_stage = self._current_stage.successor

            if self._current_stage:
                self._current_stage.theater = self
                self._current_stage.on_enter_stage()
            else:
                self.exit()

    def exit(self):
        if self._current_stage:
            self._current_stage.on_exit_stage()


class PygletTheater (Theater):

    def play(self, frames_per_sec=50):
        pyglet.clock.schedule_interval(self.update, 1/frames_per_sec)
        pyglet.app.run()

    def exit(self):
        super().exit()
        pyglet.app.exit()


class Stage:

    def __init__(self):
        self.theater = None
        self.successor = None
        self.is_finished = False

    def exit_stage(self):
        """
        Stop this stage from executing once the current update ends.
        """
        self.is_finished = True

    def exit_theater(self):
        """
        Exit the game once the current update ends.
        """
        self.theater.exit()

    def on_enter_stage(self):
        """
        Give the stage a chance to set itself up before it is updated for the 
        first time.
        """
        pass

    def on_update_stage(self, dt):
        """
        Give the stage a chance to react to each clock cycle.

        The amount of time that passed since the last clock cycle is provided 
        as an argument.
        """
        pass

    def on_exit_stage(self):
        """
        Give the stage a chance to react before it is stopped and the next 
        stage is started.
        
        You can define the next stage by setting the Stage.successor attribute.  
        If the successor is static, you can just set it in the constructor.  
        But if it will differ depending on the context, this method may be a 
        good place to calculate it because it is called only once and just 
        before the theater queries for the successor.
        """
        pass


class GameStage (Stage):

    def __init__(self, world, forum, actors):
        Stage.__init__(self)

        from .world import require_world; require_world(world)
        from .forums import require_forum; require_forum(forum)
        from .actors import require_actors; require_actors(actors)

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
        The theater terminates once all of the actors indicate that they are done.
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


class UniplayerGameStage (GameStage):

    def __init__(self, world, referee, other_actors):
        forum = Forum()
        actors = [referee] + other_actors
        GameStage.__init__(self, world, forum, actors)


class MultiplayerClientGameStage (Stage):

    def __init__(self, world, actor, pipe):
        super().__init__()
        self.forum = ClientForum(pipe)
        self.successor = GameStage(world, self.forum, [actor])

    def on_update_stage(self, dt):
        if self.forum.receive_id_from_server():
            self.exit_stage()


class MultiplayerServerGameStage (GameStage):

    def __init__(self, world, referee, pipes):
        forum = Forum()
        actors = [referee] + [ServerActor(x) for x in pipes]
        GameStage.__init__(self, world, forum, actors)




