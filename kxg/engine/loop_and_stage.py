import pyglet
from .token_and_world import Token, unrestricted_token_access
from .forum_and_actor import Forum, RemoteForum, RemoteActor

class Loop:
    """ Manage whichever stage is currently active.  This involves both
    updating the current stage and handling transitions between stages. """

    def __init__(self, initial_stage):
        self.stage = initial_stage

    def play(self, frames_per_sec=50):
        self.stage.set_loop(self)
        self.stage.on_enter_stage()

        pyglet.clock.schedule_interval(self.update, 1/frames_per_sec)
        pyglet.app.run()

    def update(self, dt):
        self.stage.on_update_stage(dt)

        if self.stage.is_finished():
            self.stage.on_exit_stage()
            self.stage = self.stage.get_successor()

            if self.stage:
                self.stage.set_loop(self)
                self.stage.on_enter_stage()
            else:
                self.exit()

    def exit(self):
        if self.stage:
            self.stage.on_exit_stage()

        pyglet.app.exit()


class GuiLoop (Loop):

    def play(self, frames_per_sec=50):
        self.window = pyglet.window.Window()
        Loop.play(self, frames_per_sec)

    def get_window(self):
        return self.window



class Stage:

    def __init__(self):
        self._stop_flag = False

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
        self.world = world
        self.forum = forum
        self.actors = actors
        self.successor = None

    def on_enter_stage(self):
        """
        Prepare the actors, the world, and the messaging system to begin 
        playing the game.
        
        This function is guaranteed to be called exactly once upon entering the 
        game stage.  Therefore it is used for initialization code.
        """

        self.forum.connect_everyone(self.world, self.actors)

        # 1. Setup the forum.

        self.forum.on_start_game()

        # 2. Setup the world.

        with unrestricted_token_access():
            self.world.on_start_game()

        # 3. Setup the actors.  Because this is done once the forum and the  
        #    world have been setup, this signals to the actors that they can 
        #    send messages and query the game world as usual.

        for actor in self.actors:
            actor.on_start_game()

    def on_update_stage(self, dt):
        """ Sequentially updates the actors, world, and messaging system.  The
        loop terminates once all of the actors indicate that they are done. """

        still_playing = False

        for actor in self.actors:
            actor.on_update_game(dt)
            if not actor.is_finished():
                still_playing = True

        if not still_playing:
            self.exit_stage()

        self.forum.on_update_game()

        with unrestricted_token_access():
            self.world.on_update_game(dt)

    def on_exit_stage(self):
        self.forum.on_finish_game()

        for actor in self.actors:
            actor.on_finish_game()

        with unrestricted_token_access():
            self.world.on_finish_game()

    def get_successor(self):
        return self.successor

    def set_successor(self, successor):
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
        self.forum = RemoteForum(pipe)

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
        actors = [referee] + [RemoteActor(x) for x in pipes]
        GameStage.__init__(self, world, forum, actors)




