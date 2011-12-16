import network
import Queue as queue

class Forum:
    """ Manages a messaging system that allows messages to be published for any
    interested subscriber to receive.  If desired, published messages will even
    be delivered across a network.  Furthermore, since the system was designed
    to work with concurrent applications, messages can be safely published at
    any time from any thread. """

    # Constructor {{{1
    def __init__(self, *pipes):
        """ Create and prepare a new forum object.  If any network connections
        are passed into the constructor, the forum will presume that other
        forums are listening and will attempt to communicate with them. """

        self.pipes = []
        self.locked = False

        self.subscriptions = {}
        self.publications = queue.Queue()

        class Publisher:
            publish = self.publish

        class Subscriber:
            subscribe = self.subscribe

        class Member:
            publish = self.publish
            subscribe = self.subscribe

        self.publisher = Publisher()
        self.subscriber = Subscriber()
        self.member = Member()

        self.setup(*pipes)

    # Attributes {{{1
    def get_publisher(self):
        return self.publisher

    def get_subscriber(self):
        return self.subscriber

    def get_member(self):
        return self.member

    # }}}1

    # Subscriptions {{{1
    def subscribe(self, flavor, callback):
        """ Attach a callback to a particular flavor of message.  For
        simplicity, the message's flavor is always the message's class.  Once
        the forum is locked, new subscriptions can no longer be made. """

        assert not self.locked

        try:
            self.subscriptions[flavor].append(callback)
        except KeyError:
            self.subscriptions[flavor] = [callback]

    # Publications {{{1
    def publish(self, message, callback=lambda: None):
        """ Publish the given message so subscribers to that class of message
        can react to it.  If any remote forums are connected, the underlying
        network connection must be capable of serializing the message. """

        publication = Publication(message, receipt=callback)
        self.publications.put(publication)

    # }}}1

    # Setup, Update, and Teardown {{{1
    def setup(self, *pipes):
        """ Connect this forum to another forum on a remote machine.  Any
        message published by either forum will be relayed to the other.  This
        method must be called before the forum is locked. """

        assert not self.locked
        self.pipes = pipes

    def update(self):
        """ Deliver any messages that have been published since the last call
        to this function.  For local messages, this requires executing the
        proper callback for each subscriber.  For remote messages, this
        involves both checking for incoming packets and relaying new
        publications across the network.  No publications can be delivered
        before the forum is locked. """

        assert self.locked

        # Add any incoming messages to the network queue.
        for pipe in self.pipes:
            for message in pipe.receive():
                publication = Publication(message, origin=pipe)
                self.publications.put(publication)

        while True:
            # Pop messages off the publication queue one at a time.
            try: publication = self.publications.get(False)
            except queue.Empty:
                break

            # Deliver the message to local subscribers.
            message = publication.message
            flavor = type(message)

            for callback in self.subscriptions.get(flavor, []):
                callback(message)

            # Deliver the message to any remote peers.
            for pipe in self.pipes:
                if pipe is not publication.origin:
                    pipe.send(message, publication.receipt)

        # Send any queued up outgoing messages.
        for pipe in self.pipes:
            for receipt in pipe.deliver():
                
                # Deliver returns a list of receipt objects for each message
                # that is successfully sent.  The forum makes sure that all of
                # these receipts are callbacks.

                receipt()

    def teardown(self):
        """ Prevent the forum from being used anymore.  This is exactly
        equivalent to calling unlock. """
        self.unlock()

    # Lock and Unlock {{{1
    def lock(self):
        """ Prevent the forum from making any more subscriptions and allow it
        to begin delivering publications. """
        self.locked = True

        for pipe in self.pipes:
            pipe.lock()

    def unlock(self):
        """ Prevent the forum from delivering messages and allow it to make new
        subscriptions.  All existing subscriptions are cleared. """
        self.locked = False

        self.subscriptions = {}
        self.publications = queue.Queue()

        for pipe in self.pipes:
            pipe.unlock()

    # }}}1

class Publication:
    """ Represents messages that are waiting to be delivered within a forum.
    Outside of the forum, this class should never be used. """

    # Constructor {{{1
    
    # The origin argument specifies the pipe that delivered this publication.
    # It is used to avoid returning a incoming message to the forum that
    # originally sent it.  For new publications, this field isn't important and
    # should not be specified.
    #
    # The receipt argument specifies a callback which will be executed
    # once the message in question is delivered.  This is only meaningful for
    # messages that originated in this forum.

    def __init__(self, message, origin=None, receipt=lambda: None):
        self.message = message
        self.origin = origin
        self.receipt = receipt

    # }}}1


# The classes below are part of an experimental messaging framework which works
# much like a conversation.  You can send requests, wait for replies, and
# things like that.  Unlike in the forum, in a conversation you are
# communicating with exactly one other client and you know who that client is.  This

class Exchange:

    # Constructor {{{1
    def __init__(self, outgoing={}, incoming={}):
        self.__outgoing = outgoing
        self.__incoming = incoming

        self.complete = False
        self.successors = ()

    # Event Handling {{{1
    def enter(self, client):
        client.outgoing_callbacks(self.__outgoing, group=self)
        client.incoming_callbacks(self.__incoming, group=self)

    def update(self, client):
        pass

    def exit(self, client):
        client.forget_group(self)

        if self.successors is None:
            self.successors = ()

    # }}}1

class Inform(Exchange):
    """ Deliver a message without expecting a response. """

    # Constructor {{{1
    def __init__(self, flavor, message, function=lambda *ignore: None):
        self.message = message
        self.complete = True

        callback = { flavor : function }
        Exchange.__init__(self, outgoing=callback)

    # Event Handling {{{1
    def enter(self, client):
        Exchange.setup(client)
        client.queue(self.message)

    # }}}1

class Request(Exchange):
    """ Send a message and wait for a response. """

    # Constructor {{{1
    def __init__(self, flavor_out, flavor_in, request, callback):
        self.request = self.request
        self.callback = self.callback

        outgoing = { flavor_out : lambda client, message: None }
        incoming = { flavor_in : self.cleanup }

        Exchange.__init__(outgoing, incoming)

    # Event Handling {{{1
    def enter(self, client):
        Exchange.setup(client)
        client.queue(self.request)

    def cleanup(self, client, message):
        self.complete = True
        self.successors = self.callback()

    # }}}1

class Reply(Exchange):
    """ Wait for a message to arrive then respond to it. """

    # Constructor {{{1
    def __init__(self, flavor_in, flavor_out, callback, successor=False):
        self.callback = callback
        self.successor = successor

        outgoing = { flavor_out : lambda client, message: None }
        incoming = { flavor_in : self.respond }

        Exchange.__init__(outgoing, incoming)

    # Event Handling {{{1
    def respond(self, client, request):
        if self.successor:  response, self.successor = self.callback(request)
        else:               response = self.callback(request)
        client.queue(response)

    # }}}1

class Conversation:
    """ Manages any number of concurrent exchanges. """ 

    # Constructor {{{1
    def __init__(self, client, *exchanges):
        self.client = client
        self.exchanges = self.execute(*exchanges)

    # }}}1

    # Update Cycle {{{1
    def setup(self):
        pass

    def update(self):
        self.client.update()

        for exchange in self.exchanges:
            exchange.update(self.client)

            if exchange.complete:
                exchange.exit(self.client)
                self.execute(*exchange.successors)

    def teardown(self):
        for exchange in self.exchanges:
            exchange.exit()

    # Exchange Management {{{1
    def execute(*exchanges):
        for exchange in exchanges:
            exchange.enter(self.client)

        self.exchanges.extend(exchanges)

    def inform(self, flavor, message):
        exchange = Inform(flavor, message)
        self.execute(exchange)

    def request(self, flavor_out, flavor_in, request, callback):
        exchange = Request(flavor_out, flavor_in, request, callback)
        self.execute(exchange)

    def reply(self, flavor_in, flavor_out, callback, successor=False):
        exchange = Reply(flavor_in, flavor_out, callback, successor)
        self.execute(exchange)

    # }}}1

