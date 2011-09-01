import errno
import socket
import struct
import pickle

# Possible Changes
# ================
# 1. Add assertions to ensure that the methods are called in the correct order.
# 2. Add a simpler socket wrapper that doesn't use callbacks.  The current
#    wrapper could inherit from the simpler one.
# 3. Add a more complicated socket wrapper that easily emulates a conversation.
#    I might also implement this is the higher-level messaging module.

class Header:
    # Specification {{{1
    # The only information stored in this header is the length of the rest
    # of the message.  This is expressed as a network byte-order (i.e.
    # big-endian) unsigned integer.

    format = "!I"
    length = struct.calcsize(format)
    # }}}1

class Host:
    """ Listens for incoming connections and creates client objects to
    handle them.  Hosts can only establish connections, so client objects have
    to be used for any real communication. """

    # Constructor {{{1
    def __init__(self, host, port):
        self.address = host, port
        self.socket = socket.socket()

        self.next_id = 1

    # Network Methods {{{1
    def setup(self, queue=5):
        """ Bind the socket to the address specified in the constructor, but
        don't begin accepting connections yet.  This should only be called
        once. """

        # The second option allows ports to be reused immediately.
        self.socket.setblocking(False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.bind(self.address)
        self.socket.listen(queue)

    def accept(self):
        """ Accept as many connections as possible without blocking.  Return a
        list of initialized connections to the client. """

        clients = []

        try:
            # Continue looping until accept() throws an exception.
            while True:
                connection, address = self.socket.accept()
                identity = self.next_id; self.next_id += 1

                try: client = self.ClientClass(*address)
                except AttributeError:
                    raise NotImplementedError

                client.attach(connection, identity)
                clients.append(client)

        except socket.error, message:

            # This message is triggered by accept() when there are no more
            # connections to accept.  
            if message.errno == errno.EAGAIN:
                return clients

            # Treat any other type of exception as a fatal error.
            else: raise

    def teardown(self):
        """ Stop accepting connections and close the host socket. """
        self.socket.close()

    # }}}1

class Client:
    """ Communicates with another connected client object over the network.
    Clients usually get initialized by connecting to a host on a published
    port, although they can also be given a pre-connected socket object.

    Once connected, clients can send and receive messages between each other.
    Callbacks can be registered for both incoming and outgoing messages.  For
    debugging purposes, any unregistered messages will raise assertion errors.

    Subclasses are expected to control how messages are converted into strings
    to be transported over the network.  This can be done by overloading the
    abstract pack() and unpack() methods. """

    # Constructor {{{1
    def __init__(self, host, port):
        self.address = host, port

        self.identity = 0
        self.socket_ready = False

        self.socket = socket.socket()
        self.socket.setblocking(False)

        self.stream_in = ""
        self.stream_out = ""

        self.clear_callbacks()

    # }}}1

# Client Identity {{{1
    def get_identity(self):
        return self.identity

    # Message Packing {{{1
    def pack(self, message):
        """ Convert a message object into a string suitable for sending across
        the network.  This method must be reimplemented in subclasses and
        should return a (type, packet) tuple. """
        raise NotImplementedError

    def unpack(self, packet):
        """ Rebuild a message object from a packet that came over the network.
        This method must be reimplemented in subclasses and should return a
        (type, message) tuple. """
        raise NotImplementedError

    # Callback Registration {{{1
    def incoming(self, flavor, function):
        """ Register the given function as a callback handler for the given
        flavor of incoming message.  Any number of callbacks can be registered
        to a single flavor of message. """

        try:
            self.callbacks_in[flavor].append(function)
        except KeyError:
            self.callbacks_in[flavor] = [function]

    def outgoing(self, flavor, function=lambda client, message: None):
        """ Allow the specified flavor of message to be sent.  An assertion
        will be thrown if an unknown message is queued for delivery.  The
        optional function parameter will be executed whenever this type of
        message is placed on the queue. """

        try:
            self.callbacks_out[flavor].append(function)
        except KeyError:
            self.callbacks_out[flavor] = [function]

    def default_incoming(self, function):
        self.default_callback_in = function

    def default_outgoing(self, function):
        self.default_callback_out = function

    def clear_callbacks(self):
        """ Stop handling any of the existing callbacks.  An assertion will be
        thrown whenever a forgotten flavor of message is received. """

        self.callbacks_in = {}
        self.callbacks_out = {}

        def unexpected_message(pipe, type, message):
            raise AssertionError, "Unexpected %s message." % type

        self.default_callback_in = unexpected_message
        self.default_callback_out = unexpected_message

    # }}}1

    # Network Setup {{{1
    def setup(self, block=False):
        """ Attempt to connect to the address specified in the constructor.
        This method will not block and will need to be called at least twice.
        If the connection is made, the return value of ready() will change from
        False to True. """

        assert not self.socket_ready

        # If the connect_ex() method returns zero, a connection was made.  If
        # it returns a nonzero value, the socket is still waiting for the
        # connection to be confirmed.  If an error occurs, an exception will be
        # thrown.

        if self.socket.connect_ex(self.address) == 0:
            self.socket_ready = True

    def ready(self):
        """ Indicate whether or not the client has been successfully connected
        to the host. """
        return self.socket_ready

    def attach(self, socket, identity):
        """ Provide the client connection with a pre-initialized socket to use.
        This method is used by hosts while accepting connections. """
        self.socket = socket
        self.identity = identity

        self.socket_ready = True
        self.socket.setblocking(False)

    def teardown(self):
        """ Stop sending or receiving messages and close the socket. """
        self.socket.close()

    # Network Methods {{{1
    def queue(self, message):
        """ Add a message to the delivery queue.  This method does not attempt
        to actually send the message, so it will never block. """

        type, data = self.pack(message)
        header = struct.pack(Header.format, len(data))

        # Execute the callbacks associated with this message type.
        default = self.default_callback_out
        wrapper = [ lambda pipe, message: default(pipe, type, message) ]

        for callback in self.callbacks_out.get(type, wrapper):
            callback(self, message)

        # Add the message to the outgoing data stream.  This is best done after
        # the callbacks are executed, because they might complain.
        self.stream_out += header + data

    def deliver(self):
        """ Send any messages that have queued up since the last call to this
        method.  If delivering a message would block, this method will just
        return and attempt to deliver it on the next call. """

        try:
            # Try to deliver all of the messages that have been queued up
            # since the last call to this method.  Save any bytes that can't
            # be sent immediately.
            delivered = self.socket.send(self.stream_out)
            self.stream_out = self.stream_out[delivered:]
        
        except socket.error, message:
            
            # This exception is triggered when no bytes at all can be sent.
            # Even though this usually indicates a serious problem, it is
            # silently ignored.
            if message.errno == errno.EAGAIN:
                return

            # Any other type of exception is taken to be a fatal error.
            else:
                raise

    def receive(self):
        """ Receive as many messages from the network as possible without
        blocking.  For each message that is received, the appropriate callback
        is executed. """

        header_format = Header.format
        header_length = Header.length

        # Begin by reading as much data as possible out of the network
        # interface and into a text stream.  If there was already data in the
        # stream, the new data it appended to it.
        while True:
            try:
                self.stream_in += self.socket.recv(4096)

            except socket.error, message:
                if message.errno == errno.EAGAIN: break
                else: raise

        # Continue by parsing as many messages as possible out of the text
        # stream.  Any incomplete data is left on the stream in the hope that
        # it will be completed later.

        while True:
            stream_length = len(self.stream_in)

            # Make sure the complete header is present, then determine the size
            # of the rest of the packet.
            if stream_length < header_length:
                break

            header = self.stream_in[:header_length]

            data_length = struct.unpack(header_format, header)[0]
            packet_length = header_length + data_length

            # Make sure that the message data is complete.  This is especially
            # important, because trying to unpack an incomplete message can
            # generate many, many different types of exceptions.
            if stream_length < packet_length:
                break

            message = self.stream_in[header_length:packet_length]
            self.stream_in = self.stream_in[packet_length:]

            type, message = self.unpack(message)

            # Handle the message by executing the proper callback.
            default = self.default_callback_in
            wrapper = [ lambda pipe, message: default(pipe, type, message) ]

            for callback in self.callbacks_in.get(type, wrapper):
                callback(self, message)

    def update(self):
        """ Simply a shorthand way to call deliver() and receive(). """
        self.deliver()
        self.receive()

    # }}}1

class RawClient(Client):
    """ Expects to be given messages that can be sent over the network without
    any modification.  The message type is taken to be everything before the
    first space, or the entire message if there are no spaces. """

    # Message Packing {{{1
    def pack(self, message):
        type = message.split(' ')[0]
        return type, message

    def unpack(self, packet):
        try:                type, message = packet.split(' ', 1)
        except ValueError:  type, message = packet, ""
        return type, message
    # }}}1

class RawHost(Host):
    """ Produces RawClient connections. """
    ClientClass = RawClient

class PickleClient(Client):
    """ Prepares message objects to be sent over the network using the pickle
    module.  This is a very general solution, but it will often use more
    bandwidth than an optimized client. """

    # Message Packing {{{1
    def pack(self, message):
        # The second parameter to dumps() tells pickle which protocol (or file
        # format) to use.  I use protocol 2 since it is optimized for new-style
        # classes and since every message class has to be new-style.
        return type(message), pickle.dumps(message, 2)

    def unpack(self, packet):
        message = pickle.loads(packet)
        return type(message), message
    # }}}1

class PickleHost(Host):
    """ Produces PickleClient connections. """
    ClientClass = PickleClient
