import errno, socket, struct, pickle

# Server Documentation
# ====================
# I had a hard time figuring out how to use the Server class.  It's not enough
# just to look at its methods, because most of them are defined in the Host
# class.  This is something that the documentation should make more clear.

class Host:
    """ Accept any number of incoming network connections.  For each
    connection, a new pipe is created.  The pipe can be used for communication,
    but by itself the host cannot. """

    def __init__(self, host, port, callback=lambda pipe: None):
        self.callback = callback
        self.queue = 5

        self.address = host, port
        self.socket = socket.socket()

        # The second option allows ports to be reused immediately.
        self.socket.setblocking(False)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.closed = False

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

        while not self.finished():

            # Continue looping until accept() throws an exception.
            try:
                connection, address = self.socket.accept()
                pipe = Pipe(connection)

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


class Server (Host):
    """ Accept a preset number of incoming network connections.  Once that
    many clients have connected, a callback will be executed to inform the
    calling code.  After that point, the server no longer does anything and can
    be safely destroyed. 
    
    Servers are more sophisticated than hosts, but they are only useful when
    you know in advance how many clients will be connecting.  If this is not
    the case, you need to use hosts instead. """

    def __init__(self, host, port, seats, callback=lambda pipes: None):
        self.pipes = []
        self.seats = seats

        def greet(pipe):
            self.pipes.append(pipe)

            if self.full():
                callback(self.pipes)
                self.close()

        Host.__init__(self, host, port, callback=greet)

    def __iter__(self):
        assert self.full()
        for pipe in zip(self.pipes, self.identities):
            yield pipe

    def get_pipes(self):
        assert self.full()
        return self.pipes

    def empty(self):
        return len(self.pipes) == 0

    def full(self):
        return len(self.pipes) == self.seats


class Client:
    """ Establish a connection to a remote machine.  Clients can connect to
    both hosts and servers.  Once the connection is established, a pipe object
    is created and the client itself can be destroyed.  All communication is
    mediated by the pipe. """

    def __init__(self, host, port, callback=lambda pipe: None):
        self.callback = callback

        self.pipe = None
        self.address = host, port

        self.socket = socket.socket()
        self.socket.setblocking(False)

    def get_pipe(self):
        return self.pipe

    def connect(self):
        assert not self.finished()

        error = self.socket.connect_ex(self.address)

        if error == 0:
            self.pipe = Pipe(self.socket)
            self.callback(self.pipe)

        return error

    def finished(self):
        return bool(self.pipe)


class Pipe:
    """ Facilitate nonblocking communication across a network connection.  
    Pipes are often not used directly, but are instead passed to higher level
    communication frameworks like forums or conversations. """

    class Header:
        """ Pack and unpack the header information that gets attached to 
        every message.  This is meant purely for internal use within pipes. """

        format = '!BI'
        length = struct.calcsize(format)

        message = 0

        @classmethod
        def pack(cls, data):
            header = struct.pack(cls.format, cls.message, len(data))
            return header + data

        @classmethod
        def unpack(cls, header_stream):
            header_type, data_length = struct.unpack(cls.format, header_stream)
            return header_type, cls.length + data_length
        

    class Serializer:
        """ Define a interface for the serialization of outgoing messages 
        and the corresponding deserialization of incoming packets. """

        def pack(self, message):
            raise NotImplementedError

        def unpack(self, packet):
            raise NotImplementedError

    class PickleSerializer (Serializer):
        """ Prepare message objects to be sent over the network using the 
        pickle module.  This is a very general solution, but it will often use 
        more bandwidth than an optimized client. """

        def pack(self, message):
            # The second parameter to dumps() tells pickle which protocol (i.e.
            # file format) to use.  I use protocol 2 since it is optimized for
            # new-style classes, and message classes tend to be new-style.
            return pickle.dumps(message, 2)

        def unpack(self, packet):
            return pickle.loads(packet)

    class NullSerializer (Serializer):
        """ Send raw objects over the network without serialization.  This is 
        an efficient approach, but it only works for strings. """
        
        def pack(self, message):
            assert isinstance(message, basestring)
            return message

        def unpack(self, packet):
            return packet


    def __init__(self, socket):
        self.socket = socket
        self.socket.setblocking(False)

        self.incoming = ""
        self.outgoing = []

        self.locked = False
        self.closed = False

        self.serializer = Pipe.PickleSerializer()
        self.serializer_stack = []

    def close(self):
        self.socket.close()
        self.closed = True
        self.unlock()

    def lock(self):
        assert not self.locked
        self.locked = True

    __enter__ = lock

    def unlock(self, *ignore):
        self.locked = False

    __exit__ = unlock

    def busy(self):
        return self.incoming or self.outgoing

    def idle(self):
        return self.incoming == "" and self.outgoing == []

    def send(self, message, receipt=None):
        assert self.locked

        data = self.serializer.pack(message)
        stream = Pipe.Header.pack(data)

        # The receipt argument allows you to provide a value that will returned
        # back to you by deliver() once this message is actually sent.  By
        # default, this value will be the message itself.

        receipt = message if receipt is None else receipt
        self.outgoing.append((stream, receipt))

    def deliver(self):
        receipts = []

        while self.outgoing:
            try:
                stream, receipt = self.outgoing[0]

                sent = self.socket.send(stream)
                self.outgoing[0] = stream[sent:], receipt

                if not self.outgoing[0][0]:
                    self.outgoing.pop(0)
                    receipts.append(receipt)

            except socket.error, message:
                
                # This exception is triggered when no bytes at all can be sent.
                # Even though this usually indicates a serious problem, it is
                # silently ignored.
                if message.errno == errno.EAGAIN: break

                # Any other flavor of exception is taken to be a fatal error.
                else: raise

        return receipts

    def receive(self):
        assert self.locked

        messages = []

        # Begin by reading as much data as possible out of the network
        # interface and into a text stream.  If there was already data in the
        # stream, the new data is appended to it.  If no bytes are returned,
        # the socket has been closed by the remote end.

        while True:
            try:
                next_packet = self.socket.recv(4096)
                self.incoming += next_packet

                if len(next_packet) == 0:
                    self.closed = True
                    break

            except socket.error, message:
                if message.errno == errno.EAGAIN: break
                else: raise

        # Continue by parsing as many messages as possible out of the text
        # stream.  Any incomplete data is left on the stream in the hope that
        # it will be completed later.

        while True:
            stream_length = len(self.incoming)
            header_length = Pipe.Header.length

            # Make sure the complete header is present, then determine the size
            # of the rest of the packet.

            if stream_length < header_length:
                break

            header_stream = self.incoming[:header_length]
            header_type, packet_length = Pipe.Header.unpack(header_stream)

            # Make sure that the message data is complete.  This is especially
            # important, because trying to unpack an incomplete message can
            # generate many, many different types of exceptions.

            if stream_length < packet_length:
                break

            data = self.incoming[header_length:packet_length]
            self.incoming = self.incoming[packet_length:]

            # Interpret the unpacked data based on the message type contained
            # in the header.  There is only one kind of message right now, but
            # that may change in the future.

            if header_type == Pipe.Header.message:
                message = self.serializer.unpack(data)
                messages.append(message)

            else:
                raise AssertionError

        return messages

    def finished(self):
        return self.closed

    def set_serializer(self, serializer):
        self.serializer = serializer

    def push_serializer(self, serializer):
        self.serializer_stack.append(self.serializer)
        self.serializer = serializer

    def pop_serializer(self):
        self.serializer = self.serializer_stack.pop()

