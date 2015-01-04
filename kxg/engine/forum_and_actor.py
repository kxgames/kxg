from .forum_observer import ForumObserver
from .token_and_world import TokenSerializer, unrestricted_token_access
from .message import CreateToken

class Forum:

    def __init__(self):
        self.world = None
        self.actors = None

    def dispatch_message(self, message):
        # This function encapsulates the message handling logic that's meant to 
        # be run on every machine participating in the game.  In other words, 
        # this code gets run more that once for each message.  For that reason, 
        # nothing in this function should make any changes to the message.  The 
        # lock() method enforces this to an extent, but it can be circumvented 
        # by mutable members so you still need to be careful.

        message.lock()

        # Normally, tokens can only call methods that have been decorated with 
        # @read_only.  This is a precaution to help keep the worlds in sync on 
        # all the clients.  This restriction is lifted when the tokens are 
        # handling messages and enforced again once the actors are handling 
        # messages.

        with unrestricted_token_access():

            # First, let the message update the state of the game world.

            message.on_execute(self.world)

            # Second, let the world react to the message.  The main effect of 
            # the message should have already been carried out above.  These 
            # callbacks should take care of more peripheral effects.

            self.world.react_to_message(message)

        # Third, let the actors and the extensions react to the message.  This 
        # step is carried out last so that the actors can be sure that the 
        # world has a consistent state by the time their handlers are called.

        for actor in self.actors:
            actor.react_to_message(message)

    def connect_everyone(self, world, actors):
        # Save references to the world and the actors in the forum.

        self.world = world
        self.actors = actors

        # Save references to the actors in the world.  The world doesn't need 
        # to know about the forum because it can't send messages.  It needs to 
        # know about the actors so it can create token extensions.

        self.world.set_actors(actors)

        # Save references to the forum and the world in the actors.  Also 
        # assign each actor a factory it can use to generate unique token ids.
        #
        # In multiplayer games, each client needs the ability to create tokens, 
        # so that messages can be instantly handled.  Tokens still need unique 
        # ids though, so this method provides each actor with an IdFactory that 
        # generates ids using an offset and a spacing to ensure uniqueness.
        #
        # Actors take their own id numbers (used for figuring out who messages 
        # were sent by) from the offset parameter of the id factory.  Since the 
        # Referee must have an id of 0 if it's present, care is taken to make 
        # that happen.

        id_factories = self._assign_id_factories()

        for actor in self.actors:
            actor.set_world(world)
            actor.set_forum(self, id_factories[actor])

    def on_start_game(self):
        pass

    def on_update_game(self):
        # The base forum doesn't do anything on a timer; it does everything in 
        # response to a message being sent.  But the RemoteForum uses this 
        # method to react to message that have arrived from the server.
        pass

    def on_finish_game(self):
        pass

    def _assign_id_factories(self):
        id_factories = {}
        actors = sorted(self.actors, key=lambda x: not isinstance(x, Referee))
        first_id = self.world.get_last_id() + 1
        spacing = len(self.actors)

        for offset, actor in enumerate(actors, first_id):
            id_factories[actor] = IdFactory(offset, spacing)

        return id_factories


class Actor (ForumObserver):

    def __init__(self):
        super().__init__()
        self.world = None
        self._forum = None
        self._id_factory = None

    def set_world(self, world):
        assert self.world is None, "Actor already has world."
        self.world = world

    def set_forum(self, forum, id_factory):
        assert self._id_factory is None, "Actor already has id."
        self._id_factory = id_factory

        assert self._forum is None, "Actor already has forum."
        self._forum = forum

    def get_id(self):
        assert self._id_factory is not None, "Actor does not have id."
        return self._id_factory.get()

    def is_finished(self):
        return self.world.has_game_ended()

    def send_message(self, message):
        # Indicate that the message was sent by this actor and give the message 
        # a chance to assign id numbers to the tokens it's creating, if it's a 
        # CreateToken message.  This is done before the message is checked so 
        # that the check can make sure valid ids were assigned.

        message.set_sender_id(self._id_factory)

        if isinstance(message, CreateToken):
            message.on_assign_token_ids(self._id_factory)

        # Make sure that the message isn't requesting something that can't be 
        # done.  For example, make sure the players have enough resource when 
        # they're trying to buy things.  If the message fails the check, return 
        # False immediately.

        if not message.on_check(self.world, self._id_factory):
            return False

        # Hand the message off to the forum to be applied to the world and 
        # relayed on to all the other actors (which may or may not be on 
        # different machines).

        self._forum.dispatch_message(message)
        return True

    def on_start_game(self):
        pass

    def on_update_game(self, dt):
        pass

    def on_finish_game(self):
        pass

    def _get_nested_observers(self):
        return (token.get_extension(self)
                for token in self.world if token.has_extension(self))


class Referee (Actor):

    class Reporter:
        
        def __init__(self, referee):
            self.referee = None
            self.is_finished_reporting = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.is_finished_reporting = True

        def send_message(self, message):
            if self.is_finished_reporting:
                raise errors.StaleReporterError()
            else:
                self.referee.send_message(message)

    def set_forum(self, forum, id_factory):
        super().set_forum(forum, id_factory)
        assert self.get_id() == 1

    def on_update_game(self, dt):
        with Referee.Reporter(self) as reporter:
            for token in self.world:
                token.on_report_to_referee(reporter)


class RemoteForum (Forum):

    def __init__(self, pipe):
        super().__init__()
        self.actor_id_factory = None
        self.pipe = pipe
        self.pipe.lock()

    def receive_id_from_server(self):
        """
        Listen for an id from the server.

        At the beginning of a game, each client receives an IdFactory from the 
        server.  This factory are used to give id numbers that are guaranteed 
        to be unique to tokens that created locally.  This method checks to see 
        if such a factory has been received  This method checks to see if such 
        a factory has been received.  If it hasn't, this method does not block 
        and immediately returns False.  If it has, this method returns True 
        after saving the factory internally.  At this point it is safe to enter 
        the GameStage.
        """
        for message in self.pipe.receive():
            if isinstance(message, IdFactory):
                self.actor_id_factory = message
                return True
        return False

    def dispatch_message(self, message):
        # Have the message update the local world like usual.

        super().dispatch_message(message)

        # Relay the message to a RemoteActor running on the server to update 
        # the world on all of the other machine playing the game as well.

        self.pipe.send(message)
        self.pipe.deliver()

    def dispatch_soft_sync_error(self, message):
        """
        Manage the response when the server reports a soft sync error.

        A soft sync error can happen when this client sends a message that 
        fails the check on the server.  If the reason for the failure isn't 
        very serious, then the server can decide to send it as usual in the 
        interest of a smooth gameplay experience.  When this happens, the 
        message is flagged as a soft sync error.

        The purpose of a soft sync error is to inform the clients that they 
        have become slightly out of sync with the server and to give them a 
        chance to get back in sync.  When a message is marked as a sync error, 
        it is also given the opportunity to save the information from the 
        server that would have prevented the error from occurring in the first 
        place.  Note that sync errors are only handled on clients.
        """

        # Synchronize the world.

        with unrestricted_token_access():
            message.on_soft_sync_error(self.world)
            self.world.react_to_soft_sync_error(message)

        # Synchronize the tokens.

        for actor in self.actors:
            actor.react_to_soft_sync_error(message)

    def dispatch_hard_sync_error(self, message):
        """
        Manage the response when the server reports a hard sync error.

        A hard sync error is produced when this client sends a message that the 
        server refuses to pass on to the other clients playing the game.  In 
        this case, the client must either undo the changes that the message 
        made to the world before being sent or crash.  Note that unlike a soft 
        sync error, a hard sync error is only reported to the client that sent 
        the offending message.
        """

        # Roll back changes that the original message made to the world.

        with unrestricted_token_access():
            message.on_hard_sync_error(self.world)
            self.world.react_to_hard_sync_error(message)

        # Give the actors a chance to react to the error.  For example, a 
        # GUI actor might inform the user that there are connectivity 
        # issues and that their last action was countermanded.

        for actor in self.actors:
            actor.react_to_hard_sync_error(message)

    def connect_everyone(self, world, actors):
        # Make sure that this forum is only connected to one actor.

        assert len(actors) == 1
        self.actor = actors[0]

        # Connect the forum, world, and actors as usual.

        super().connect_everyone(world, actors)

    def on_start_game(self):
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self):
        # An attempt is made to immediately deliver any messages passed into 
        # relay_message(), but sometimes it takes more than one try to send a 
        # message.  So in case there are any messages waiting to be sent, the 
        # code below attempts to clear the queue every frame.

        self.pipe.deliver()

        # For each message received from the server:

        for message in self.pipe.receive():

            # Execute messages coming in from other clients.  Messages that are 
            # coming back in after being sent by this client have already been 
            # executed.  They are only being sent back because an error has 
            # been detected and needs to be handled.

            if not message.was_sent_by(self.actor_id_factory):
                super().dispatch_message(message)

            # If an incoming message has any error flags set, attempt to handle 
            # those as well.  A message coming from any client can have a soft 
            # sync error, but only messages that came from this client can have 
            # a hard sync error.

            if message.has_soft_sync_error():
                self.dispatch_soft_sync_error(message)

            if message.has_hard_sync_error():
                self.dispatch_hard_sync_error(message)

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _assign_id_factories(self):
        assert self.actor_id_factory is not None
        return {self.actor: self.actor_id_factory}


class RemoteActor (Actor):

    def __init__(self, pipe):
        super().__init__()
        self._disable_forum_observation()

        self.pipe = pipe
        self.pipe.lock()

    def set_forum(self, forum, id):
        super().set_forum(forum, id)
        self.pipe.send(id)

    def is_finished(self):
        return self.pipe.finished() or Actor.is_finished(self)

    def send_message(self):
        raise NotImplementedError

    def react_to_message(self, message):
        if not message.was_sent_by(self._id_factory):
            self.pipe.send(message)
            self.pipe.deliver()

    def on_start_game(self):
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self, dt):
        # For each message received from the connected client:

        for message in self.pipe.receive():

            # Check the message to make sure it matches the state of the game 
            # world on the server.  If the message doesn't pass the check, the 
            # client and server must be out of sync.  Decide whether the sync 
            # error is recoverable (i.e. soft) or not (i.e. hard).  Soft sync 
            # errors are relayed on to the rest of the game as usual and are 
            # given an opportunity to sync all the clients.  Hard sync errors 
            # are not not relayed and must be somehow undone on the client that 
            # sent the message.
            
            if not message.on_check(self.world, self._id_factory):
                if message.on_check_for_soft_sync_error(self.world):
                    message.flag_soft_sync_error()
                    self.pipe.send(message)
                else:
                    message.flag_hard_sync_error()
                    self.pipe.send(message)
                    continue

            # Silently reject the message if it was sent by an actor with a 
            # different id that this one.  This should absolutely never happen 
            # because this actor gives its id to its client, so if a mismatch 
            # is detected we've mostly likely received some sort of malformed 
            # or malicious packet.

            if not message.was_sent_by(self._id_factory):
                continue

            # Execute the message if it hasn't been rejected yet.

            self._forum.dispatch_message(message)

        # Deliver any messages waiting to be sent.  This has to be done every 
        # frame because it sometimes takes more than one try to send a message.

        self.pipe.deliver()

    def on_finish_game(self):
        self.pipe.pop_serializer()


class IdFactory:

    def __init__(self, offset, spacing):
        self.offset = offset
        self.spacing = spacing
        self.num_ids_assigned = 0

    def __contains__(self, id):
        return id % self.spacing == self.offset

    def get(self):
        return self.offset

    def next(self):
        next_id = self.num_ids_assigned * self.spacing + self.offset
        self.num_ids_assigned += 1
        return next_id



def handle_message(message_cls):
    def decorator(function):
        function._handle_message = message_cls
        return function
    return decorator

def handle_soft_sync_error(message_cls):
    def decorator(function):
        function._handle_soft_sync_error = message_cls
        return function
    return decorator

def handle_hard_sync_error(message_cls):
    def decorator(function):
        function._handle_hard_sync_error = message_cls
        return function
    return decorator



