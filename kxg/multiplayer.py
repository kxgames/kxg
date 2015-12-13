from .errors import *
from .forums import Forum, IdFactory
from .actors import Actor

class ClientForum(Forum):

    def __init__(self, pipe):
        super().__init__()
        self.pipe = pipe
        self.pipe.lock()

        from collections import OrderedDict

        self.actor_id_factory = None
        self.response_id_factory = IdFactory(0, 1)
        self.sent_message_cache = OrderedDict()

    def receive_id_from_server(self):
        """
        Listen for an id from the server.

        At the beginning of a game, each client receives an IdFactory from the 
        server.  This factory are used to give id numbers that are guaranteed 
        to be unique to tokens that created locally.  This method checks to see if such 
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

    def connect_everyone(self, world, actors):
        # Make sure that this forum is only connected to one actor.

        assert len(actors) == 1
        self.actor = actors[0]

        # Connect the forum, world, and actors as usual.

        super().connect_everyone(world, actors)

    def execute_message(self, message):
        # Cache the message and give it an id number the server can reference 
        # in its response.  Messages are cached so they can be undone if they 
        # are rejected by the server.  The id is necessary so the client forum 
        # (i.e. this object) can associate each response with a cached message.

        message._set_server_response_id(self.response_id_factory.next())
        self.sent_message_cache[message._get_server_response_id()] = message

        # Relay the message to a ServerActor running on the server to update 
        # the world on all of the other machines playing the game as well.

        self.pipe.send(message)
        self.pipe.deliver()

        # Have the message update the local world like usual.

        super().execute_message(message)

    def execute_sync(self, message):
        """
        Respond when the server indicates that the client is out of sync.

        The server can request a sync when this client sends a message that 
        fails the check() on the server.  If the reason for the failure isn't 
        very serious, then the server can decide to send it as usual in the 
        interest of a smooth gameplay experience.  When this happens, the 
        server sends out an extra response providing the clients with the
        information they need to resync themselves.
        """
        info("synchronizing a message: {message}")

        # Synchronize the world.

        with self.world._unlock_temporarily():
            message._sync(self.world)
            self.world._react_to_sync_response(message)

        # Synchronize the tokens.

        for actor in self.actors:
            actor._react_to_sync_response(message)

    def execute_undo(self, message):
        """
        Manage the response when the server reports a hard sync error.

        A hard sync error is produced when this client sends a message that the 
        server refuses to pass on to the other clients playing the game.  In 
        this case, the client must either undo the changes that the message 
        made to the world before being sent or crash.  Note that unlike a soft 
        sync error, a hard sync error is only reported to the client that sent 
        the offending message.
        """
        info("undoing a message: {message}")

        # Roll back changes that the original message made to the world.

        with self.world._unlock_temporarily():
            message._undo(self.world)
            self.world._react_to_undo_response(message)

        # Give the actors a chance to react to the error.  For example, a 
        # GUI actor might inform the user that there are connectivity 
        # issues and that their last action was countermanded.

        for actor in self.actors:
            actor._react_to_undo_response(message)

    def on_start_game(self):
        from .tokens import TokenSerializer
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self):
        from .messages import Message

        # An attempt is made to immediately deliver any messages passed into 
        # execute_message(), but sometimes it takes more than one try to send a 
        # message.  So in case there are any messages waiting to be sent, the 
        # code below attempts to clear the queue every frame.

        self.pipe.deliver()

        # For each message received from the server:

        for packet in self.pipe.receive():

            # If the incoming packet is a message, execute it on this client 
            # and, if necessary, synchronize this client's world with the 
            # server's.  Messages that were sent from this client will not 
            # reappear here, so we don't need to worry about double-dipping.

            if isinstance(packet, Message):
                info("receiving a message: {packet}")
                super().execute_message(packet)
                response = packet._get_server_response()
                if response and response.sync_needed:
                    self.execute_sync(packet)

            # If the incoming packet is a response to a message sent from this 
            # client, find that message in the "sent message cache" and attach 
            # the response to it.  The response is handled in the while loop 
            # below (and not right here) to better handle weird cases that can 
            # occur when several messages are sent between server responses.

            elif isinstance(packet, ServerResponse):
                message = self.sent_message_cache[packet.id]
                message._set_server_response(packet)

        # Try to clear the sent message cache:

        while self.sent_message_cache:
            message = self.sent_message_cache[next(reversed(self.sent_message_cache))]
            response = message._get_server_response()

            # Don't handle any response until responses for any messages that 
            # were sent after it have been handled.  This keeps the world in a 
            # sane state for every response.

            if response is None:
                break

            # If the server requested that a message sync or undo itself, then 
            # do that.  Messages coming from any client may need to be synced, 
            # but messages that need to be undone were sent by this client and 
            # rejected by the server.

            if response.sync_needed:
                self.execute_sync(message)
            if response.undo_needed:
                self.execute_undo(message)

            # Now that the message has been fully handled, pop it off the 
            # cache.

            self.sent_message_cache.popitem()

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _assign_id_factories(self):
        assert self.actor_id_factory is not None
        return {self.actor: self.actor_id_factory}


class ServerActor(Actor):

    def __init__(self, pipe):
        super().__init__()
        self._disable_forum_observation()
        self.pipe = pipe
        self.pipe.lock()

    def send_message(self, message):
        raise NotImplementedError

    def on_start_game(self, num_players):
        from .tokens import TokenSerializer
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self, dt):
        from .messages import MessageCheck

        # For each message received from the connected client:

        for message in self.pipe.receive():
            info("received a message: {message}")

            # Make sure the message wasn't sent by an actor with a different id 
            # than this one.  This should absolutely never happen because this 
            # actor gives its id to its client, so if a mismatch is detected 
            # there's probably a bug in the game engine.

            if not message.was_sent_by(self._id_factory):
                critical("ignoring message from player {self.id} claiming to be from player {message.sender_id}.")
                continue

            # Check the message to make sure it matches the state of the game 
            # world on the server.  If the message doesn't pass the check, the 
            # client and server must be out of sync, because the same check was 
            # just passed on the client.

            response = ServerResponse(message)
            try:
                message._check(self.world)
            except MessageCheck:
                response.sync_needed = True
            else:
                response.sync_needed = False

            # Decide if it will be enough for the clients to sync themselves, 
            # or if this message shouldn't be relayed at all (and should be 
            # undone on the client that sent it).  The message is also given a 
            # chance to store information it can use later to sync the game. 

            if response.sync_needed:
                response.undo_needed = not message._prepare_sync(
                        self.world, response)

            # Tell the clients how to treat this message.  For the client that 
            # sent the message in the first place, the response is sent on its 
            # own.  If a sync or an undo is needed, the client will retrieve 
            # the original message from its cache and use it to reconcile its 
            # world with the server's.  Otherwise, the client will just clear 
            # the original message from its cache.  For all the other clients, 
            # the response is attached to the message, but only if a sync is 
            # needed (otherwise nothing special needs to be done).

            self.pipe.send(response)

            # If the message doesn't have an irreparable sync error, execute it 
            # on the server and relay it to all the other clients.

            if not response.undo_needed:
                self._forum.execute_message(message)

        # Deliver any messages waiting to be sent.  This has to be done every 
        # frame because it sometimes takes more than one try to send a message.

        self.pipe.deliver()

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _set_forum(self, forum, id):
        super()._set_forum(forum, id)
        self.pipe.send(id)

    def _relay_message(self, message):
        """
        Relay messages from the forum on the server to the client represented 
        by this actor.
        """
        info("relaying a message: {message}")

        if not message.was_sent_by(self._id_factory):
            self.pipe.send(message)
            self.pipe.deliver()

    def _react_to_message(self, message):
        """
        Don't ever change the world in response to a message.

        This method is defined is called by the game engine to trigger 
        callbacks tied by this actor to particular messages.  This is useful 
        for ordinary actors, but remote actors are only meant to shuttle 
        message between clients and should never react to individual messages.
        """
        pass


class ServerResponse:

    def __init__(self, message):
        self.id = message._get_server_response_id()
        self.sync_needed = False
        self.undo_needed = False

    def __repr__(self):
        return "{}(sync_needed={}, undo_needed={})".format(
                self.__class__.__name__, self.sync_needed, self.undo_needed)
    

