import network
import Queue as queue

class Subscribe(object):
    """ Contains information about a message being subscribed to.  The network
    connection must support objects of this type. """

    def __init__(self, flavor):
        self.flavor = flavor

class Publish(object):
    """ Contains information about a message being published.  The network
    connection must support objects of this type. """

    def __init__(self, message):
        self.message = message

class Broker(object):
    """ Manages a messaging system that allows messages to be published for any
    interested subscriber to receive.  If desired, published messages will even
    be delivered across a network.  Furthermore, since the system was designed
    to work with concurrent applications, messages can be published at any time
    from any thread. """

    def __init__(self, *clients):
        """ Create and prepare a new broker object.  If any network connections
        are passed into the constructor, the broker will presume that other
        brokers are listening on the other ends and will attempt to communicate
        with them. """

        self.clients = clients
        self.messages = queue.Queue()

        # The first dictionary is used to map flavors to local callbacks.  The
        # second dictionary is used to map flavors to remote brokers.
        self.subscriptions = {}
        self.destinations = {}

        def incoming_publication(pipe, publication):
            message = publication.message
            self.messages.put(message)

        def incoming_subscription(pipe, subscription):
            flavor = subscription.flavor
            self.destinations[flavor] = pipe

        for clients in self.clients:
            client.outgoing(Publish)
            client.outgoing(Subscribe)

            client.incoming(Publish, incoming_publication)
            client.incoming(Subscribe, incoming_subscription)

    def deliver(self):
        """ Deliver any messages that have been published since the last call
        to this function.  For local messages, this requires executing the
        proper callback for each subscriber.  For remote messages, this
        involves both checking for incoming packets and relaying new
        publications across the network. """
        
        for client in self.clients:
            client.update()

        for message in self.messages:
            flavor = type(message)
            callbacks = self.subscriptions[flavor]

            for callback in callbacks:
                callback(message)

        self.messages = []

    def publish(self, message):
        """ Publish the given message so subscribers to that class of
        message can react to it.  If remote brokers have also subscribed to
        the message, it will be wrapped into a packet and relayed to them as
        well.  Make sure that the resulting packet is supported by the
        underlying network connection.  This method is thread-safe. """

        flavor = type(message)
        publication = Publish(message)

        for client in self.destinations[flavor]:
            client.queue(publication)

        self.messages.put(message)

    def subscribe(self, flavor, callback):
        """ Attach a callback to a particular flavor of message.  For
        simplicity, the message's flavor is always the message's class.  Remote
        brokers are informed of each subscription made so that they can relay
        any relevant publications to this broker.  """

        try:
            self.subscriptions[flavor].append(callback)
        except KeyError:
            self.subscriptions[flavor] = [callback]

        subscription = Subscribe(flavor)
        for client in self.clients:
            client.queue(subscription)

