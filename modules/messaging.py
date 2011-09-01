import network
import Queue as queue

class Broker(object):
    """ Manages a messaging system that allows messages to be published for any
    interested subscriber to receive.  If desired, published messages will even
    be delivered across a network.  Furthermore, since the system was designed
    to work with concurrent applications, messages can be published at any time
    from any thread. """

    # Constructor {{{1
    def __init__(self, *pipes):
        """ Create and prepare a new broker object.  If any network connections
        are passed into the constructor, the broker will presume that other
        brokers are listening and will attempt to communicate with them. """

        self.pipes = []
        self.messages = queue.Queue()

        # The first dictionary is used to map flavors to local callbacks.  The
        # second dictionary is used to map flavors to remote brokers.
        self.subscriptions = {}
        self.destinations = {}

        self.locked = False
        self.connect(*pipes)

    # Network Setup {{{1
    def connect(self, *pipes):
        """ Attach the broker to another broker on a remote machine.  Any
        message published by either broker will be relayed to the other.  This
        method must be called before the broker is locked. """

        assert not self.locked

        def incoming_publication(pipe, type, msg): self.messages.put(msg)
        def outgoing_publication(pipe, type, msg): pass

        for pipe in pipes:
            pipe.default_incoming(incoming_publication)
            pipe.default_outgoing(outgoing_publication)

            self.pipes.append(pipe)

    # }}}1

    # Subscriptions {{{1
    def subscribe(self, flavor, callback):
        """ Attach a callback to a particular flavor of message.  For
        simplicity, the message's flavor is always the message's class.  Once
        the broker is locker, new subscriptions can no longer be made. """

        assert not self.locked

        if flavor not in self.subscriptions:
            self.subscriptions[flavor] = set()

        self.subscriptions[flavor].add(callback)

    def lock(self):
        """ Prevent the broker from making any more subscriptions, but allow
        the broker to begin publishing and delivering messages. """
        self.locked = True

    # Publications {{{1
    def publish(self, message):
        """ Publish the given message so subscribers to that class of message
        can react to it.  If remote brokers have also subscribed to the
        message, it will be relayed to them as well.  The underlying network
        connection must be capable of serializing the given message.  This
        method is thread-safe and cannot be called before the broker gets
        locked. """

        assert self.locked

        self.messages.put(message)

        for pipe in self.pipes:
            pipe.queue(message)

    def deliver(self):
        """ Deliver any messages that have been published since the last call
        to this function.  For local messages, this requires executing the
        proper callback for each subscriber.  For remote messages, this
        involves both checking for incoming packets and relaying new
        publications across the network.  This method cannot be called before
        the broker is locked. """

        assert self.locked
        
        for pipe in self.pipes:
            pipe.update()

        while True:
            try: message = self.messages.get(False)
            except queue.Empty: break

            flavor = type(message)
            callbacks = self.subscriptions[flavor]

            for callback in callbacks:
                callback(message)

    # }}}1
