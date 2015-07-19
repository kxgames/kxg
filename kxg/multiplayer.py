from .errors import *
from .forums import Forum, IdFactory
from .actors import Actor

class ClientForum (Forum):

    class CachedMessage:

        def __init__(self, message):
            self.message = message
            self.response = None

        @property
        def has_response(self):
            return self.response is not None


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

    def dispatch_message(self, message):
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

        super().dispatch_message(message)

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

        with self.world._unlock_temporarily():
            message._sync(self.world)
            self.world._react_to_soft_sync_error(message)

        # Synchronize the tokens.

        for actor in self.actors:
            actor._react_to_soft_sync_error(message)

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

        with self.world._unlock_temporarily():
            message._undo(self.world)
            self.world._react_to_hard_sync_error(message)

        # Give the actors a chance to react to the error.  For example, a 
        # GUI actor might inform the user that there are connectivity 
        # issues and that their last action was countermanded.

        for actor in self.actors:
            actor._react_to_hard_sync_error(message)

    def connect_everyone(self, world, actors):
        # Make sure that this forum is only connected to one actor.

        assert len(actors) == 1
        self.actor = actors[0]

        # Connect the forum, world, and actors as usual.

        super().connect_everyone(world, actors)

    def on_start_game(self):
        from .tokens import TokenSerializer
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self):
        from .messages import Message

        # An attempt is made to immediately deliver any messages passed into 
        # dispatch_message(), but sometimes it takes more than one try to send 
        # a message.  So in case there are any messages waiting to be sent, the 
        # code below attempts to clear the queue every frame.

        self.pipe.deliver()

        # For each message received from the server:

        for packet in self.pipe.receive():

            # If the incoming packet is a message, execute it on this client 
            # and, if necessary, synchronize this client's world with the 
            # server's.  Messages that were sent from this client will not 
            # reappear here, so we don't need to worry about double-dipping.

            if isinstance(packet, Message):
                super().dispatch_message(packet)
                response = packet._get_server_response()
                if response and response.sync_needed:
                    self.dispatch_soft_sync_error(packet)

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

            if response is None: break

            # If the server requested that a message sync or undo itself, then 
            # do that.  Messages coming from any client may need to be synced, 
            # but messages that need to be undone were sent by this client and 
            # rejected by the server.

            if response.sync_needed:
                self.dispatch_soft_sync_error(message)
                # self._sync_message() ?
            if response.undo_needed:
                self.dispatch_hard_sync_error(message)
                # self._undo_message() ?

            # Now that the message has been fully handled, pop it off the 
            # cache.

            self.sent_message_cache.popitem()

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _assign_id_factories(self):
        assert self.actor_id_factory is not None
        return {self.actor: self.actor_id_factory}


class ServerActor (Actor):

    def __init__(self, pipe):
        super().__init__()
        self._disable_forum_observation()
        self.pipe = pipe
        self.pipe.lock()

    def send_message(self):
        raise NotImplementedError

    def on_start_game(self):
        from .tokens import TokenSerializer
        serializer = TokenSerializer(self.world)
        self.pipe.push_serializer(serializer)

    def on_update_game(self, dt):
        # For each message received from the connected client:

        for message in self.pipe.receive():

            # Silently reject the message if it was sent by an actor with a 
            # different id that this one.  This should absolutely never happen 
            # because this actor gives its id to its client, so if a mismatch 
            # is detected we've mostly likely received some sort of malformed 
            # or malicious packet.

            if not message._was_sent_by(self._id_factory):
                continue

            # Check the message to make sure it matches the state of the game 
            # world on the server.  If the message doesn't pass the check, the 
            # client and server must be out of sync, because the same check was 
            # just passed on the client.

            response = ServerResponse(message)
            response.sync_needed = not message._check(
                    self.world, self._id_factory)

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
                self._forum.dispatch_message(message)

        # Deliver any messages waiting to be sent.  This has to be done every 
        # frame because it sometimes takes more than one try to send a message.

        self.pipe.deliver()

    def on_finish_game(self):
        self.pipe.pop_serializer()

    def _set_forum(self, forum, id):
        super()._set_forum(forum, id)
        self.pipe.send(id)

    def _dispatch_message(self, message):
        """
        Relay messages from the forum on the server to the client represented 
        by this actor.
        """
        if not message._was_sent_by(self._id_factory):
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
    

