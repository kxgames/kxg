import errno, socket, struct, pickle

# Missing Tests
# =============
# 1. Client.relay()

class Header(object):
    # Specification {{{1

    # This is mostly bullshit
    # -----------------------
    # The only information stored in this header is the length of the rest of
    # the message.  This is expressed as a network byte-order (i.e. big-endian)
    # unsigned integer.

    format = "!bHII"
    length = struct.calcsize(format)

    @staticmethod
    def identity(receiver):
        return Header.pack(1, receiver, 0, 0)

    @staticmethod
    def message(client, message):
        length = len(message)
        origin, ticker = client.identity, client.message_ticker

        return Header.pack(2, origin, ticker, length), (origin, ticker)

    @staticmethod
    def duplicate(tag, message):
        length = len(message)
        origin, ticker = tag

        return Header.pack(2, origin, ticker, length)

    @staticmethod
    def pack(type, client, identity, length):
        format = Header.format
        return struct.pack(format, type, client, identity, length)

    @staticmethod
    def unpack(stream):
        format = Header.format
        length = Header.length

        header = stream[:length]
        type, origin, ticker, data_length = struct.unpack(format, header)

        # Type 1: Identity message.
        if type == 1:
            identity = origin
            message_tag = False

        # Type 2: Regular message.
        elif type == 2:
            identity = False
            message_tag = origin, ticker

        else:
            error = "Unable to read incoming packet header."
            raise AssertionError(error)

        return identity, message_tag, data_length

    # }}}1

class Host(object):
    """ Listens for incoming connections and creates client objects to
    handle them.  Hosts can only establish connections, so client objects have
    to be used for any real communication. """

    # Constructor {{{1
    def __init__(self, host, port):
        self.address = host, port
        self.socket = socket.socket()

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
                client = self.client(*address)

                client.attach(connection)
                clients.append(client)

        except socket.error, message:

            # This message is triggered by accept() when there are no more
            # connections to accept.  
            if message.errno == errno.EAGAIN:
                return clients

            # Treat any other flavor of exception as a fatal error.
            else: raise

    def client(self, host, port):
        """ Create and return a new client instance.  This needs to be
        reimplemented in concrete subclasses to return a client of the
        appropriate flavor. """
        raise NotImplementedError

    def teardown(self):
        """ Stop accepting connections and close the host socket. """
        self.socket.close()

    # }}}1

class Server(Host):
    """ Optimized host for client-server architectures. """

    # Constructor {{{1
    def __init__(self, host, port, seats, callback=lambda client: None):
        Host.__init__(self, host, port)

        self.clients = []

        self.seats = seats
        self.callback = callback

        self.identity = 1
        self.next_identity = 2

        self.empty()
        self.full()

    def __iter__(self):
        for client in self.clients:
            yield client

    # Network Methods {{{1
    def accept(self):
        for client in Host.accept(self):
            if self.full(): return

            client.adopt_identity(self.identity)
            client.bestow_identity(self.next_identity)

            self.next_identity += 1

            self.callback(client)
            self.clients.append(client)

    def update(self):
        for client in self.clients:
            client.update()

    def broadcast(self, message):
        for client in self.clients:
            client.queue(message)

    def empty(self):
        return len(self.clients) == 0

    def full(self):
        return len(self.clients) == self.seats

    def members(self):
        return self.clients

    # }}}1

class Client(object):
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

        self.socket = socket.socket()
        self.socket.setblocking(False)

        self.socket_ready = False

        self.stream_in = ""
        self.stream_out = ""

        self.identity = 0
        self.message_ticker = 1

        self.forget_everything()

    def __iter__(self):
        yield self

    # }}}1

    # Client Identity {{{1
    def identify(self):
        return self.identity

    def adopt_identity(self, identity):
        error = "Identity numbers must be greater than 0."
        assert identity > 0, error

        self.identity = identity

    def bestow_identity(self, identity):
        error = "Cannot assign an identity before the pipe is initialized."
        assert self.socket_ready, error

        error = "Identity numbers must be greater than 0."
        assert identity > 0, error

        self.stream_out += Header.identity(identity)

    # Message Packing {{{1
    def pack(self, message):
        """ Convert a message object into a string suitable for sending across
        the network.  This method must be reimplemented in subclasses and
        should return a (flavor, packet) tuple. """
        raise NotImplementedError

    def unpack(self, packet):
        """ Rebuild a message object from a packet that came over the network.
        This method must be reimplemented in subclasses and should return a
        (flavor, message) tuple. """
        raise NotImplementedError

    # }}}1

    # Default Callbacks {{{1
    def outgoing_default(self, callback, group=None):
        """ Set the default callback for outgoing messages.  This callback is
        only called if nothing else matches the outgoing message. """
        self.defaults_out[group] = callback

    def incoming_default(self, callback, group=None):
        """ Set the default callback for incoming messages.  This callback is
        only called if nothing else matches the incoming message. """
        self.defaults_in[group] = callback

    # Registered Callbacks {{{1
    def outgoing(self, flavor, function=lambda *ignore: None, group=None):
        """ Register a single, unnamed, outgoing callback.  This is simply a
        convenient wrapper around outgoing_callbacks(). """
        callbacks = { flavor : function }
        return self.outgoing_callbacks(callbacks, group)

    def incoming(self, flavor, function, group=None):
        """ Register a single, unnamed, incoming callback.  This is simply a
        convenient wrapper around incoming_callbacks(). """
        callbacks = { flavor : function }
        return self.incoming_callbacks(callbacks, group)

    # Make callback() an alias for incoming().
    callback = incoming

    def outgoing_flavors(self, flavors, group=None):
        """ Allow the specified flavors of message to be sent.  Normally,
        sending an unregistered flavor of message triggers an assertion. """

        callback = lambda pipe, message: None
        callbacks = { flavor : callback for flavor in flavors }

        self.outgoing_callbacks(group, callbacks)

    def outgoing_callbacks(self, callbacks, group=None):
        """ Register handlers for any number of outgoing message flavors.  If a
        group name is given, the callbacks will be associated with that group.
        Otherwise they are kept in an unnamed group. """

        for flavor, function in callbacks.items():
            try:
                self.callbacks_out[flavor][group] = function
            except KeyError:
                self.callbacks_out[flavor] = { group : function }

    def incoming_callbacks(self, callbacks, group=None):
        """ Register handlers for any number of incoming message flavors.  If a
        group name is given, the callbacks will be associated with that group.
        Otherwise they are kept in an unnamed group. """

        for flavor, function in callbacks.items():
            try:
                self.callbacks_in[flavor][group] = function
            except KeyError:
                self.callbacks_in[flavor] = { group : function }

    # Forgetting Callbacks {{{1
    def forget_group(self, group=None):
        """ Stop handling every callback registered to the given group.  This
        includes both registered and default callbacks. """

        if group in self.defaults_in:   del self.defaults_in[group]
        if group in self.defaults_out:  del self.defaults_out[group]

        for callbacks in self.callbacks_in.values():
            if group in callbacks: del callbacks[group]

        for callbacks in self.callbacks_out.values():
            if group in callbacks: del callbacks[group]

    def forget_everything(self):
        """ Stop handling every callback the client knows about, registered and
        default, incoming and outgoing. """

        self.defaults_in = {}
        self.defaults_out = {}

        self.callbacks_in = {}
        self.callbacks_out = {}

    # }}}1

    # Network Maintenance {{{1
    def setup(self):
        """ Attempt to connect to the address specified in the constructor.
        This method will not block and will need to be called at least twice.
        If the connection is made, the return value of ready() will change from
        False to True. """

        error = "Cannot reinitialize a pipe."
        assert not self.socket_ready, error

        # If the connect_ex() method returns zero, a connection was made.
        # Otherwise the socket is still waiting for the connection to be
        # confirmed.  If an error occurs, an exception will be thrown.
        if self.socket.connect_ex(self.address) == 0:
            self.socket_ready = True

    def ready(self):
        """ Indicate whether or not the client has been successfully connected
        to the host. """
        return self.socket_ready

    def attach(self, socket):
        """ Provide the client connection with a pre-initialized socket to use.
        This method is used by hosts while accepting connections. """

        error = "Cannot attach a socket to an initialized pipe."
        assert not self.socket_ready, error

        self.socket = socket
        self.socket_ready = True

        self.socket.setblocking(False)

    def update(self):
        """ Simply a shorthand way to call deliver() and receive(). """

        if self.ready():
            self.receive()
            self.deliver()
        else:
            self.setup()

    def teardown(self):
        """ Stop sending or receiving messages and close the socket.  This will
        silently do nothing if the socket has not been initialized yet. """
        self.socket.close()
        self.socket_ready = False

    # Outgoing Messages {{{1
    def queue(self, message, tag):
        """ Add a message to the delivery queue.  This method does not attempt
        to actually send the message, so it will never block. """

        # Prepare the given message to be sent over the network.
        flavor, data = self.pack(message)
        header, tag = Header.message(self, data)

        # Find the correct callback to execute.
        callbacks = self.callbacks_out.get(flavor, {}).values()
        defaults = self.defaults_out.values()

        def apply(functions, *arguments, **keywords):
            for function in functions:
                function(*arguments, **keywords)

        if callbacks:   apply(callbacks, self, tag, message)
        elif defaults:  apply(defaults, self, tag, flavor, message)
        else:
            error = "Surprised by outgoing %s message." % flavor
            raise AssertionError(error)

        # Add the message to the outgoing data stream.  To keep the output
        # stream clean even if a callback fails, this should be done after all
        # the callbacks are executed.
        self.stream_out += header + data
        self.message_ticker += 1

    def duplicate(self, tag, message):
        """ Resend a message using exactly the same header as it originally
        had. """

        flavor, data = self.pack(message)
        header = Header.duplicate(tag, data)
        self.stream_out += header + data

    def deliver(self):
        """ Send any messages that have queued up since the last call to this
        method.  If delivering a message would block, this method will just
        return and attempt to deliver it on the next call. """

        error = "Cannot deliver messages before the pipe is initialized."
        assert self.socket_ready, error

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

            # Any other flavor of exception is taken to be a fatal error.
            else:
                raise

    # Incoming Messages {{{1
    def receive(self):
        """ Receive as many messages from the network as possible without
        blocking.  For each message that is received, the appropriate callback
        is executed. """

        error = "Cannot receive messages before the pipe is initialized."
        assert self.socket_ready, error

        # This function helps execute callbacks.
        def apply(functions, *arguments, **keywords):
            for function in functions:
                function(*arguments, **keywords)

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
            header_length = Header.length

            # Make sure the complete header is present, then determine the size
            # of the rest of the packet.
            if stream_length < header_length:
                break

            header_data = Header.unpack(self.stream_in)

            identity, message_tag, data_length = header_data
            packet_length = header_length + data_length

            # Make sure that the message data is complete.  This is especially
            # important, because trying to unpack an incomplete message can
            # generate many, many different types of exceptions.
            if stream_length < packet_length:
                break

            data = self.stream_in[header_length:packet_length]
            self.stream_in = self.stream_in[packet_length:]

            if identity:
                self.identity = identity

            else:
                tag = message_tag
                flavor, message = self.unpack(data)

                # Find the correct callback to execute.
                callbacks = self.callbacks_in.get(flavor, {}).values()
                defaults = self.defaults_in.values()

                if callbacks:   apply(callbacks, self, tag, message)
                elif defaults:  apply(defaults, self, tag, flavor, message)
                else:
                    error = "Surprised by incoming %s message." % flavor
                    raise AssertionError(error)

    # }}}1

class RawHost(Host):
    # Client Factory {{{1
    def client(self, host, port):
        return RawClient(host, port)
    # }}}1

class RawServer(Server):
    # Client Factory {{{1
    def client(self, host, port):
        return RawClient(host, port)
    # }}}1

class RawClient(Client):
    """ Expects to be given messages that can be sent over the network without
    any modification.  The message flavor is taken to be everything before the
    first space, or the entire message if there are no spaces. """

    # Message Packing {{{1
    def pack(self, message):
        flavor = message.split(' ')[0]
        return flavor, message

    def unpack(self, packet):
        try:                flavor, message = packet.split(' ', 1)
        except ValueError:  flavor, message = packet, ""
        return flavor, message
    # }}}1

class EasyHost(Host):
    # Client Factory {{{1
    def __init__(self, host, port, integrate=lambda input: input):
        Host.__init__(self, host, port)
        self.integrate = integrate

    def client(self, host, port):
        return EasyClient(host, port, integrate=self.integrate)
    # }}}1

class EasyServer(Server):
    # Client Factory {{{1
    def __init__(self, host, port, seats,
            callback=lambda client: None, integrate=lambda input: input):

        Server.__init__(self, host, port, seats, callback)
        self.integrate = integrate

    def client(self, host, port):
        return EasyClient(host, port, integrate=self.integrate)
    # }}}1

class EasyClient(Client):
    """ Prepares message objects to be sent over the network using the pickle
    module.  This is a very general solution, but it will often use more
    bandwidth than an optimized client. """

    # Constructor {{{1
    def __init__(self, host, port, integrate=lambda input: input):
        Client.__init__(self, host, port)
        self.integrate = integrate

    # Message Packing {{{1
    def pack(self, message):
        # The second parameter to dumps() tells pickle which protocol (i.e.
        # file format) to use.  I use protocol 2 since it is optimized for
        # new-style classes and since every message class has to be new-style.
        return type(message), pickle.dumps(message, 2)

    def unpack(self, packet):
        message = pickle.loads(packet)
        message = self.integrate(message)
        return type(message), message
    # }}}1

