import network
import Queue as queue

# Forum Permissions
# =================
# I think it would be good to provide a way to limit access to the forum.  For
# example, some objects should only have read privileges, some should only have
# write privileges, and some should be able to do either.  One way to enforce
# these restrictions is to add three satellite classes: Publisher, Subscriber,
# and Member.
#
# These classes would be incomplete wrappers around the base Forum
# functionality.  For example, Publisher would contain a reference to the forum
# but would only implement publish().  Likewise, Subscriber would
# only implement subscribe().  Member would be able to do both.
#
# In python, it would still be possible to use the base Forum directly.  In
# more structured languages, though, I could make this impossible.

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
        self.history = {}

        self.subscriptions = {}
        self.publications = queue.Queue()

        self.locked = False
        self.setup(*pipes)

    # Setup and Teardown {{{1
    def setup(self, *pipes):
        """ Connect this forum to another forum on a remote machine.  Any
        message published by either forum will be relayed to the other.  This
        method must be called before the forum is locked. """

        assert not self.locked

        def incoming_publication(pipe, tag, type, message):
            origin, ticker = tag
            old_ticker = self.history.get(origin, 0)

            if ticker > old_ticker:
                publication = pipe, tag, message
                self.publications.put(publication)

                self.history[origin] = ticker

        def outgoing_publication(pipe, tag, type, message):
            origin, ticker = tag
            self.history[origin] = ticker

        for pipe in pipes:
            pipe.incoming_default(incoming_publication, group=self)
            pipe.outgoing_default(outgoing_publication, group=self)

            self.pipes.append(pipe)

    def teardown(self):
        """ Disconnect this forum from any forum over the network.  The pipes
        that were being used to communicate with the remote forums will still
        be active, they just won't relay any incoming messages to this forum
        anymore. """

        for pipe in self.pipes:
            pipe.forget_group(self)

        self.pipes = []
        self.history = {}

        self.subscriptions = {}
        self.publications = queue.Queue()

        self.locked = False
        self.setup()
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

    def lock(self):
        """ Prevent the forum from making any more subscriptions and allow it
        to begin delivering publications. """
        self.locked = True

    # Publications {{{1
    def publish(self, message):
        """ Publish the given message so subscribers to that class of message
        can react to it.  If any remote forums are connected, the underlying
        network connection must be capable of serializing the message. """

        pipe = tag = None
        publication = pipe, tag, message

        self.publications.put(publication)

    def deliver(self):
        """ Deliver any messages that have been published since the last call
        to this function.  For local messages, this requires executing the
        proper callback for each subscriber.  For remote messages, this
        involves both checking for incoming packets and relaying new
        publications across the network.  No publications can be delivered
        before the forum is locked. """

        assert self.locked
        
        # Add any incoming messages to the network queue.
        for pipe in self.pipes:
            pipe.receive()

        while True:
            # Pop messages off the publication queue one at a time.
            try:
                publication = self.publications.get(False)
                sender, tag, message = publication

            except queue.Empty:
                break

            # Deliver the message to local subscribers.
            flavor = type(message)
            callbacks = self.subscriptions.get(flavor, [])

            for callback in callbacks:
                callback(message)

            # Deliver the message to any remote peers.
            for pipe in self.pipes:
                if pipe is not sender:
                    pipe.queue(message, tag)

        # Send any queued up outgoing messages.
        for pipe in self.pipes:
            pipe.deliver()

    # }}}1

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
    """ Manages any number of concurrent shits. """ 

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

