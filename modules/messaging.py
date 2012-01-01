import network
import Queue as queue

from utilities.infinity import *

class Forum:
    """ Manages a messaging system that allows messages to be published for any
    interested subscriber to receive.  If desired, published messages will even
    be delivered across a network.  Furthermore, since the system was designed
    to work with concurrent applications, messages can be safely published at
    any time from any thread. """

    # Constructor {{{1
    def __init__(self, *pipes, **options):
        """ Create and prepare a new forum object.  If any network connections
        are passed into the constructor, the forum will presume that other
        forums are listening and will attempt to communicate with them. """

        self.pipes = []
        self.locked = False

        self.subscriptions = {}
        self.publications = queue.Queue()

        safety_flag = options.get("safe", True)

        self.incoming_limit = 1 if safety_flag else infinity
        self.incoming_publications = []

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

    # Access Control {{{1
    def get_member(self):
        return self.member

    def get_publisher(self):
        return self.publisher

    def get_subscriber(self):
        return self.subscriber

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
        self.pipes.extend(pipes)

    def update(self):
        """ Deliver any messages that have been published since the last call
        to this function.  For local messages, this requires executing the
        proper callback for each subscriber.  For remote messages, this
        involves both checking for incoming packets and relaying new
        publications across the network.  No publications can be delivered
        before the forum is locked. """

        assert self.locked

        # Accept any messages that came in over the network since the last
        # update.  Not all of these messages will necessarily delivered this
        # time.  Those that aren't will be stored and delivered later.
        
        for pipe in self.pipes:
            for message in pipe.receive():
                publication = Publication(message, origin=pipe)
                self.incoming_publications.append(publication)

        # Decide how many messages to deliver.  It is safer to deliver only
        # one, because this eliminates some potential race conditions.
        # However, sometimes this performance hit is unacceptable.

        iteration = 0
        while True:
            iteration += 1

            if iteration < self.incoming_limit:
                break
            if not self.incoming_publications:
                break

            publication = self.incoming_publications.pop(0)
            self.publications.put(publication)

        while True:
            # Pop messages off the publication queue one at a time.
            try: 
                publication = self.publications.get(False)

                # Deliver the message to local subscribers.
                message = publication.message
                flavor = type(message)

                for callback in self.subscriptions.get(flavor, []):
                    callback(message)

                # Deliver the message to any remote peers.
                for pipe in self.pipes:
                    if pipe is not publication.origin:
                        pipe.send(message, publication.receipt)

            except queue.Empty:
                break

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

class Conversation:

    """ Manages a messaging system that allows two participants to carry out
    brief conversations.  During the conversation, each participant can easily
    transition back and forth between sending requests and waiting for
    responses.  These transitions are setup in advance, and played out after
    the conversation starts. """
    
    # Constructor {{{1
    def __init__(self, pipe, *exchanges):
        self.pipe = pipe
        self.exchanges = exchanges
        self.closed = False

    # }}}1

    # Setup Methods {{{1
    def setup(self, *exchanges):
        self.exchanges += exchanges

    def start(self, *exchanges):
        self.pipe.lock()
        self.setup(*exchanges)

    # Update Methods {{{1
    def update(self):
        self.update_outgoing()
        self.update_incoming()
        self.update_finished()

        return self.finished()

    def update_outgoing(self):
        for exchange in self.exchanges:
            message = exchange.send()
            if message is not None:
                self.pipe.send(message)

        self.pipe.deliver()
        self.update_exchanges()

    def update_incoming(self):
        for message in self.pipe.receive():
            for exchange in self.exchanges:
                exchange.receive(message)
            self.update_exchanges()

    def update_exchanges(self):
        self.exchanges = [ exchange.next()
                for exchange in self.exchanges
                if not exchange.finish() ]

    def update_finished(self):
        if not self.exchanges and self.pipe.idle():
            self.finish()

    # Teardown Methods {{{1
    def finish(self):
        self.pipe.unlock()

        self.exchanges = []
        self.closed = True

    def finished(self):
        return self.closed

    # }}}1

class SimpleSend(Conversation):

    """ Sends a single message and finishes without waiting for a response.
    This class is intended only for brief exchanges with SimpleReceive.  It
    should not be used in more complex protocols. """

    # Setup {{{1
    def __init__(self, pipe, message):
        send = Send(message); finish = Finish()
        send.transition(finish)

        Conversation.__init__(self, pipe, send)

    # }}}1

class SimpleReceive(Conversation):

    """ Waits to receive a single message, then finishes.  This class is meant
    to be used with SimpleSend, and should not be used in more complicated
    protocols. """

    # Setup {{{1
    def __init__(self, pipe, flavor, callback=lambda message: None):
        self.receive = Receive(); finish = Finish()
        self.receive.transition(finish, flavor, callback)

        Conversation.__init__(self, pipe, self.receive)

    def get_message(self):
        return self.receive.get_message()

    # }}}1

class SimpleRequest(Conversation):

    """ Sends a single message and waits to receive a response.  This class is
    can be used, in conjunction with SimpleResponse, to request that
    information be sent over the network. """

    # Setup {{{1
    def __init__(self, pipe, message, flavor, callback):
        request = Send(message)
        response = Receive()
        finish = Finish()

        request.transition(response)
        response.transition(finish, flavor, callback)

        Conversation.__init__(self, pipe, request)
        self.response = response

    def get_response(self):
        return self.response.get_message()

    # }}}1

class SimpleResponse(Conversation):

    """ Waits to receive a request, then respond with a predefined response.
    This class is meant to be used with SimpleRequest to reply to simple
    requests. """

    # Setup {{{1
    def __init__(self, pipe, flavor, message):
        request = Receive()
        response = Send(message)
        finish = Finish()

        request.transition(response, flavor)
        request.transition(finish)

        Conversation.__init__(self, pipe, request)

    # }}}1

class FullRequest(Conversation):

    """ Sends a request and waits for it to either be accepted or rejected.
    This class is a wrapper around a conversation and a number of different
    exchanges, meant to be useful in the most common situations.  If you want
    to make a custom conversation, this may be useful to look at. """

    # Setup {{{1
    def __init__(self, pipe, message, accept_flavor, reject_flavor):

        # Begin by setting up all the exchanges that can happen on this side
        # of the conversation.  Once the request is sent, the conversation
        # will begin listening for a confirmation from its partner.  Once that
        # confirmation is received, the conversation ends and reports either
        # accept or reject, as appropriate.
        
        request = Send(message); reply = Receive()

        def accept_callback(): self.result = True
        def reject_callback(): self.result = False

        accept = Finish(accept_callback)
        reject = Finish(reject_callback)

        request.transition(reply)

        def save_response(message): self.response = message

        reply.transition(accept, accept_flavor, save_response)
        reply.transition(reject, reject_flavor, save_response)

        # Once the exchanges have been set up properly, create and store a
        # conversation object.  The second argument to the constructor
        # indicates that the conversation will begin by sending the request.

        Conversation.__init__(self, pipe, request)

        self.result = False
        self.response = None

    # Attributes {{{1
    def get_accepted(self):
        assert self.finished()
        return self.finished() and self.result

    def get_rejected(self):
        assert self.finished()
        return self.finished() and not self.result

    def get_response(self):
        assert self.finished()
        return self.response

    # }}}1

class FullResponse(Conversation):

    """ Waits for a request to arrive and, once it does, decides whether or not
    to accept it.  This class is meant to work with the request class above.
    Normally the request will come from the client side and the response from
    the server side. """

    # Setup {{{1
    def __init__(self, pipe, flavor_callback, accept_message, reject_message):

        # Begin by setting up all the exchanges that can happen on this side of
        # the conversation.  Once a request is received, it is evaluated using
        # the given callback.  If the callback returns True, the request is
        # accepted and the conversation is finished.  Otherwise, it is rejected
        # and another request is awaited.

        request = Receive(flavor_callback)

        accept = Send(accept_message)
        reject = Send(reject_message)

        def save_request(message): self.request = message

        request.transition(accept, True, save_request)
        request.transition(reject, False, save_request)

        finish = Finish()

        accept.transition(finish)
        reject.transition(request)

        Conversation.__init__(self, pipe, request)
        self.request = None

    # Attributes {{{1
    def get_request(self):
        assert self.finished()
        return self.request

    # }}}1

###############################################################################
# The classes beyond this point are primarily intended for use within the
# classes above this point.  Some of these classes can still be used on their
# own, but are only necessary in unusual situations, while others should never
# be directly used.  Just be sure you know what you are doing.

class Exchange:

    """ Represents a single exchange in a conversation.  The basic examples,
    which are all implemented by subclasses below, include sending messages,
    receiving messages, and ending the conversation.  Complex conversations can
    be created by linking a number of these exchanges together. """
    
    # Interface Definition {{{1
    def send(self):
        """ Returns a message that should be sent to the other end of the
        conversation.  Be careful, because this method will be called every
        update cycle for as long as the exchange lasts. """
        return None

    def receive(self, message):
        """ Accepts a message that was received from the other end of the
        conversation.  The message is not necessarily relevant to this
        exchange, but in many cases it will cause a transition to occur. """
        pass

    def next(self):
        """ Returns the exchange that should be executed on the next update
        cycle.  To remain in the same exchange, return self. """
        raise NotImplementedError

    def finish(self):
        """ Returns true if this side of the conversation is over.  The
        conversation itself will keep updating until all outgoing and incoming
        messages have been completely sent and received, respectively. """
        return False

    # }}}1

class Send(Exchange):

    """ Sends a message and immediately transitions to a different exchange.
    That exchange must be specified before the conversation starts. """

    # Constructor {{{1
    def __init__(self, message):
        self.message = message
        self.exchange = None

    # Interface Methods {{{1
    def send(self):
        return self.message

    def transition(self, exchange):
        self.exchange = exchange

    def next(self):
        return self.exchange

    # }}}1

class Receive(Exchange):

    """ Waits for a message to be received, then transitions the conversation
    to another exchanges based on the content of the message.  Different types
    of messages can cause different transitions.  The message type is the
    message class by default, but this can be controlled by a callback. """

    # Constructor and Attributes {{{1
    def __init__(self, flavor=lambda message: type(message)):
        self.flavor = flavor

        # The received attribute contains the last message received, no matter
        # what its type is.  This allows receive() to communicate with next().

        self.received = None
        
        # The messages list contains all of the messages that were received and
        # recognized.  New messages are pushed onto the front of this list, so
        # the last message can be found at the 0th index.

        self.messages = []

        self.exchanges = {}
        self.callbacks = {}

    def get_message(self, index=0):
        return self.messages[index]

    def get_messages(self):
        return self.messages

    # Interface Methods {{{1
    def receive(self, message):
        self.received = message

    def transition(self, exchange, flavor, callback=lambda message: None):
        self.exchanges[flavor] = exchange
        self.callbacks[flavor] = callback

    def next(self):
        message, self.received = self.received, None
        transition = self

        if message is not None:
            flavor = self.flavor(message)
            transition = self.exchanges.get(flavor, self)

        if transition is not self:
            self.callbacks[flavor](message)
            self.messages.insert(0, message)
        
        return transition

    # }}}1

class Finish(Exchange):

    """ Ends the conversation without sending or receiving anything.  Note that
    this does not end the conversation running on the far side of the
    connection. """

    # Constructor {{{1
    def __init__(self, callback=lambda: None):
        self.callback = callback

    # Interface Methods {{{1
    def finish(self):
        self.callback()
        return True

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

