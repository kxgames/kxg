import errno, socket, struct, pickle

# Server Documentation
# ====================
# I had a hard time figuring out how to use the Server class.  It's not enough
# just to look at its methods, because most of them are defined in the Host
# class.  This is something that the documentation should make more clear.

class Host:
    """ Accepts any number of incoming network connections.  For each
    connection, a new pipe is created.  The pipe can be used for communication,
    but by itself the host cannot. """

    # Constructor {{{1
    def __init__(self, port, queue=5, callback=lambda pipe: None):
        self.callback = callback
        self.queue = queue

        self.address = '', port
        self.socket = socket.socket()

        # The second option allows ports to be reused immediately.
        self.socket.setblocking(False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.closed = False
        self.next_identity = 1

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
                pipe = self.instantiate(connection)

                # Assign the pipe a unique identity.
                identity = self.next_identity
                self.next_identity += 1

                with pipe:
                    pipe.greet(identity)
                    pipe.deliver()

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
    """ Accepts a preset number of incoming network connections.  Once that
    many clients have connected, a callback will be executed to inform the
    calling code.  After that point, the server no longer does anything and can
    be safely destroyed. 
    
    Servers are more sophisticated than hosts, but they are only useful when
    you know in advance how many clients will be connecting.  If this is not
    the case, you need to use hosts instead. """

    # Constructor {{{1
    def __init__(self, port, seats, callback=lambda pipes: None):
        self.pipes = []
        self.seats = seats

        def greet(pipe):
            self.pipes.append(pipe)

            if self.full():
                callback(self.pipes)
                self.close()

        Host.__init__(self, port, queue=seats, callback=greet)

    def __iter__(self):
        assert self.full()
        for pipe in zip(self.pipes, self.identities):
            yield pipe

    # Pipe Access {{{1
    def get_pipes(self):
        assert self.full()
        return self.pipes

    def empty(self):
        return len(self.pipes) == 0

    def full(self):
        return len(self.pipes) == self.seats

    # }}}1

class Client:
    """ Establishes a connection to a remote machine.  Clients can connect to
    both hosts and servers.  Once the connection is established, a pipe object
    is created and the client itself can be destroyed.  All communication is
    mediated by the pipe. """

    # Constructor {{{1
    def __init__(self, host, port, identity=0, callback=lambda pipe: None):
        self.callback = callback
        self.identity = identity

        self.pipe = None
        self.address = host, port

        self.socket = socket.socket()
        self.socket.setblocking(False)

    # Pipe Access {{{1
    def get_pipe(self):
        return self.pipe

    # Pipe Creation {{{1
    def connect(self):
        if self.pipe and not self.pipe.get_identity():
            with self.pipe:
                self.pipe.receive()

            if self.pipe.get_identity():
                self.callback(self.pipe)

        elif self.socket.connect_ex(self.address) == 0:
            socket = self.socket
            identity = self.identity

            self.pipe = self.instantiate(socket)

        else:
            pass

    def finished(self):
        return self.pipe and self.pipe.get_identity()

    # }}}1

class Pipe:
    """ Allows nonblocking communication across a network connection.  Pipes
    are often not used directly, but instead passed to higher level
    communication frameworks, like the forum. """

    # Constructor {{{1
    def __init__(self, socket):
        self.socket = socket
        self.identity = 0

        self.stream_in = ""
        self.stream_out = ""

        self.locked = False
        self.pending_deliveries = []

        self.socket.setblocking(False)

    # Socket Destruction {{{1
    def idle(self):
        return self.stream_in == self.stream_out == ""

    def close(self):
        self.socket.close()
        self.unlock()

    # }}}1

    # Message Packing {{{1
    def pack(self, message):
        """ Convert a message object into a string suitable for sending across
        the network.  This method must be reimplemented in subclasses and
        should return a data string. """
        raise NotImplementedError

    def unpack(self, packet):
        """ Rebuild a message object from a packet that came over the network.
        This method must be reimplemented in subclasses and should return a
        data string. """
        raise NotImplementedError

    # Identity Access {{{1
    def get_identity(self):
        return self.identity

    # Locking and Unlocking {{{1

    # The purpose of these two methods is to allow higher level messaging
    # frameworks to be sure that they have exclusive use of this pipe.  If the
    # pipe is already locked, it has to be unlocked before another framework
    # can use it.

    def lock(self):
        assert not self.locked
        self.locked = True

    def unlock(self, *ignore):
        self.locked = False

    __enter__ = lock
    __exit__ = unlock

    # }}}1

    # Outgoing Messages {{{1
    def greet(self, identity):
        assert self.locked
        assert not self.identity

        greeting = Greeting.pack(identity)
        stream = Header.pack_greeting(greeting)

        self.identity = identity
        self.stream_out += stream

        delivery = len(stream), None
        self.pending_deliveries.append(delivery)

    def send(self, message, receipt=None):
        assert self.locked
        assert self.identity

        data = self.pack(message)
        stream = Header.pack_message(data)

        # The receipt argument allows you to provide a value that will returned
        # back to you by deliver() once this message is actually sent.  By
        # default, this value will be the message itself.

        receipt = message if receipt is None else receipt
        delivery = len(stream), receipt

        self.stream_out += stream
        self.pending_deliveries.append(delivery)

    def deliver(self):
        assert self.locked

        receipts = []

        try:
            # Deliver as much data as possible without blocking.
            bytes_delivered = self.socket.send(self.stream_out)
            self.stream_out = self.stream_out[bytes_delivered:]

        except socket.error, message:
            
            # This exception is triggered when no bytes at all can be sent.
            # Even though this usually indicates a serious problem, it is
            # silently ignored.
            if message.errno == errno.EAGAIN: pass

            # Any other flavor of exception is taken to be a fatal error.
            else: raise

        else:

            # Each pending delivery contains two pieces of information: the
            # length of that delivery and a receipt object to return if it has
            # been completely sent.  This loop finds all of the deliveries that
            # have been successfully sent, removes then from the list of
            # pending deliveries, and returns the appropriate receipt objects.

            bytes_confirmed = 0

            while self.pending_deliveries:
                bytes, receipt = self.pending_deliveries.pop(0)

                bytes_confirmed += bytes
                bytes_remaining = bytes_confirmed - bytes_delivered

                if bytes_remaining > 0:

                    # This is triggered when the message has only been been
                    # partially sent.  The message is placed back on the
                    # pending delivery queue, but its length is reset to the
                    # number of bytes that have not yet been delivered.

                    delivery_remaining = bytes_remaining, receipt
                    self.pending_deliveries.insert(0, delivery_remaining)

                    # After this is done, the loop needs to be exited.  If it
                    # isn't, the pending deliveries queue will be destroyed.

                    break

                else:
                    receipts.append(receipt)

        return receipts

    def deliver_everything(self):
        assert self.locked

        # This is a blocking version of deliver.  Continue delivering messages
        # until none are left.

        receipts = []
        while self.stream_out:
            receipts += self.deliver()

        return receipts

    # Incoming Messages {{{1
    def receive(self):
        assert self.locked

        messages = []

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

            header_stream = self.stream_in[:header_length]
            header_type, packet_length = Header.unpack(header_stream)

            # Make sure that the message data is complete.  This is especially
            # important, because trying to unpack an incomplete message can
            # generate many, many different types of exceptions.

            if stream_length < packet_length:
                break

            data = self.stream_in[header_length:packet_length]
            self.stream_in = self.stream_in[packet_length:]

            # Interpret the unpacked data based on the message type contained
            # in the header.  Greetings are a special type of message used to
            # assign a common identity to both ends of a pipe.

            if header_type == Header.message:
                assert self.identity
                message = self.unpack(data)
                messages.append(message)

            elif header_type == Header.greeting:
                assert self.identity == 0
                self.identity = Greeting.unpack(data)

            else:
                raise AssertionError

        return messages

    # }}}1

class Header:
    """ Packs and unpacks the header information that gets attached to every
    message.  This is meant purely for internal use within pipes. """

    # Header Format {{{1
    format = '!BI'
    length = struct.calcsize(format)

    message = 0
    greeting = 1

    @classmethod
    def pack_greeting(cls, data):
        header = struct.pack(cls.format, cls.greeting, len(data))
        return header + data

    @classmethod
    def pack_message(cls, data):
        header = struct.pack(cls.format, cls.message, len(data))
        return header + data

    @classmethod
    def unpack(cls, header_stream):
        header_type, data_length = struct.unpack(cls.format, header_stream)
        return header_type, cls.length + data_length
    
    # }}}1
    
class Greeting:
    """ Packs and unpacks a greeting messages.  These messages have special
    meaning to pipes and are used to assign identities across the network. """

    # Greeting Format {{{1
    format = '!I'
    length = struct.calcsize(format)

    @classmethod
    def pack(cls, identity):
        return struct.pack(cls.format, identity)

    @classmethod
    def unpack(cls, data):
        return struct.unpack(cls.format, data)[0]

    # }}}1

class PickleFactory:
    """ Provides an instantiate() method that crates PicklePipe objects.  This
    method needs to be redefines in the host, client, and server classes. """

    # Factory Method {{{1
    def instantiate(self, socket):
        return PicklePipe(socket)
    
    # }}}1

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

        return pickle.dumps(message, 2)

    def unpack(self, packet):
        return pickle.loads(packet)

    # }}}1

