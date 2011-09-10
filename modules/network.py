import errno, socket, struct, pickle

class Host:

    # Constructor {{{1
    def __init__(self, port, identity, queue=5, callback=lambda pipe: None):
        self.identity = identity
        self.callback = callback
        self.queue = queue

        self.address = '', port
        self.socket = socket.socket()

        # The second option allows ports to be reused immediately.
        self.socket.setblocking(False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.closed = False

    # Pipe Creation {{{1
    def open(self):
        """ Bind the socket to the address specified in the constructor, but
        don't begin accepting connections yet.  This should only be called
        once. """

        self.socket.bind(self.address)
        self.socket.listen(self.queue)

    def accept(self):
        """ Accept as many connections as possible without blocking.  Return a
        list of initialized connections to the client. """

        error = "This host is no longer accepting connections."
        assert not self.finished(), error

        try:
            # Continue looping until accept() throws an exception.
            while not self.finished():
                connection, address = self.socket.accept()
                pipe = self.instantiate(connection, self.identity)

                self.callback(pipe)

        except socket.error, message:

            # This message is triggered by accept() when there are no more
            # connections to accept.  
            if message.errno == errno.EAGAIN: return

            # Treat any other flavor of exception as a fatal error.
            else: raise

    def finished(self):
        return self.closed

    def close(self):
        """ Stop accepting connections and close the host socket. """
        self.socket.close()
        self.closed = True

    # }}}1

class Server(Host):

    # Constructor {{{1
    def __init__(self, port, seats, callback=lambda pipe: None):
        self.pipes = []
        self.seats = seats

        identity = 1
        self.next_identity = 2

        def greet(pipe):
            identity = self.next_identity
            self.next_identity += 1

            pipe.greet(identity)
            pipe.deliver()

            self.pipes.append(pipe)

            if self.full():
                callback(self.pipes)
                self.close()

        Host.__init__(self, port, identity, queue=seats, callback=greet)

    def __iter__(self):
        for pipe in self.pipes:
            yield pipe

    # Attributes {{{1
    def get_pipes(self):
        return self.pipes

    def empty(self):
        return len(self.pipes) == 0

    def full(self):
        return len(self.pipes) == self.seats

    # }}}1

class Client:

    # Constructor {{{1
    def __init__(self, host, port, identity=0, callback=lambda pipe: None):
        self.callback = callback
        self.identity = identity

        self.pipe = None
        self.address = host, port

        self.socket = socket.socket()
        self.socket.setblocking(False)

    # Attributes {{{1
    def get_pipe(self):
        return self.pipe

    # Pipe Creation {{{1
    def connect(self):
        if self.pipe and not self.pipe.get_identity():
            self.pipe.receive(0)

            if self.pipe.get_identity():
                self.callback(self.pipe)

        elif self.socket.connect_ex(self.address) == 0:
            socket = self.socket
            identity = self.identity

            self.pipe = self.instantiate(socket, identity)

        else:
            pass

    def finished(self):
        return self.pipe and self.pipe.get_identity()

    # }}}1

class Header:

    # Header Format {{{1
    format = "!HHII"
    length = struct.calcsize(format)

    # Header Packing {{{1
    @classmethod
    def pack(cls, tag, data):
        target, origin, ticker = tag; length = len(data)
        return struct.pack(cls.format, target, origin, ticker, length)

    # Header Unpacking {{{1
    @classmethod
    def unpack(cls, stream):
        format = cls.format; length = cls.length
        header = stream[:length]

        target, origin, ticker, data_length = struct.unpack(format, header)
        message_tag = target, origin, ticker

        return message_tag, data_length

    # }}}1

class Pipe:

    # Constructor {{{1
    def __init__(self, socket, identity):
        self.socket = socket
        self.identity = identity

        self.targets = set()
        self.messages = dict()

        self.stream_in = ""
        self.stream_out = ""

        self.message_ticker = 1

        self.socket.setblocking(False)

    # Attributes {{{1
    def get_identity(self):
        return self.identity

    # }}}1

    # Target Registration {{{1
    def register(self, target):
        assert target is not 0
        assert target not in self.targets
        self.targets.add(target)

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

    # Disconnecting {{{1
    def close(self):
        self.socket.close()
    # }}}1

    # Outgoing Messages {{{1
    def greet(self, identity):
        target = 0; padding = 0; data = ''
        tag = target, identity, padding

        self.stream_out += Header.pack(tag, data)

    def send(self, target, message):
        assert target in self.targets

        tag = target, self.identity, self.message_ticker
        flavor, data = self.pack(message)

        header = Header.pack(tag, data)

        self.stream_out += header + data
        self.message_ticker += 1

        return tag, flavor

    def resend(self, tag, message):
        flavor, data = self.pack(message)
        header = Header.pack(tag, data)

        self.stream_out += header + data
        return tag, flavor

    def deliver(self):

        try:
            # Deliver as much data as possible without blocking.
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
    def receive(self, target):
        if target == 0: assert self.identity == 0
        else:           assert self.identity != 0

        # Begin by reading as much data as possible out of the network
        # interface and into a text stream.  If there was already data in the
        # stream, the new data is appended to it.
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

            message_tag, data_length = Header.unpack(self.stream_in)
            packet_length = header_length + data_length

            # Make sure that the message data is complete.  This is especially
            # important, because trying to unpack an incomplete message can
            # generate many, many different types of exceptions.
            if stream_length < packet_length:
                break

            data = self.stream_in[header_length:packet_length]
            self.stream_in = self.stream_in[packet_length:]

            target, origin, ticker = message_tag

            if target == 0:
                assert self.identity == 0
                self.identity = origin

            else:
                flavor, message = self.unpack(data)
                package = message_tag, flavor, message

                try:
                    self.messages[target].append(package)
                except KeyError:
                    self.messages[target] = [package]

        return self.messages.pop(target, [])

    # }}}1

class PickleFactory:
    def instantiate(self, socket, identity):
        return PicklePipe(socket, identity)

class PickleHost(Host, PickleFactory): pass
class PickleServer(Server, PickleFactory): pass
class PickleClient(Client, PickleFactory): pass

class PicklePipe(Pipe):
    """ Prepares message objects to be sent over the network using the pickle
    module.  This is a very general solution, but it will often use more
    bandwidth than an optimized client. """

    # Message Packing {{{1
    def pack(self, message):
        # The second parameter to dumps() tells pickle which protocol (i.e.
        # file format) to use.  I use protocol 2 since it is optimized for
        # new-style classes and since every message class has to be new-style.
        return type(message), pickle.dumps(message, 2)

    def unpack(self, packet):
        message = pickle.loads(packet)
        return type(message), message

    # }}}1

