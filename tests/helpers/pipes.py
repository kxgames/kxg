# This path module tweaks sys.path and needs to be called before any module
# from this package is imported.

import os, path
import struct

from network import PickleHost, PickleServer, PickleClient

# Messages {{{1
class Message(object):

    def __init__(self, bytes=8):
        self.data = os.urandom(bytes)

    def __eq__(self, other):
        return self.data == other.data

    def __hash__(self):
        format = "H"    # Unsigned short
        length = struct.calcsize(format)

        values = struct.unpack(format, self.data[:length])
        return values[0]

    def __repr__(self):
        return str(hash(self))

class FirstMessage(Message): pass
class SecondMessage(Message): pass
class ThirdMessage(Message): pass

# Inbox {{{1
class Inbox(list):

    def receive(self, *arguments):
        message = arguments[-1]
        self.append(message)

    def check(self, outbox, shuffled=False):
        error = "sent %s; received %s" % (outbox, self)
        if shuffled:        assert set(self) == set(outbox), error
        if not shuffled:    assert self == outbox, error

# Outbox {{{1
class Outbox(list):

    def __init__(self, *messages, **flavors):
        list.__init__(self, messages)

        defaults = {
                "first"     : FirstMessage,
                "second"    : SecondMessage,
                "third"     : ThirdMessage,
                "default"   : Message }

        self.flavors = flavors if flavors else defaults

    def flavor(self, flavor="default"):
        return self.flavors[flavor]

    def message(self, bytes=8, flavor="default"):
        Message = self.flavors[flavor]
        return Message(bytes)

    def send_message(self, bytes=8, flavor="default"):
        message = self.message(bytes, flavor)
        self.send(message)
        return message

    def send(self, *arguments):
        message = arguments[-1]
        self.append(message)


# }}}1

# Connect {{{1
def connect(pipes=1, reverse=False, integrate=lambda x: x):
    host, port = 'localhost', 10236

    # Create a web of client server connections.  The pickle family of socket
    # wrappers are used for convenience.
    server = PickleServer(port, pipes)
    clients = [ PickleClient(host, port) for each in range(pipes) ]

    # Have the server start listening to the given port.  No clients should be
    # connected at this point.
    server.open()
    
    assert server.empty();
    assert not server.finished()

    # Connect each of the clients to the server.  The connect() method for the
    # clients has to be called a number of times.
    for client in clients:
        client.connect();   assert not client.finished()
        client.connect();   assert not client.finished()

        server.accept();    assert not server.empty()
        client.connect();   assert client.finished()

    # Make sure that the server has stopped accepting new connections.
    assert server.full()
    assert server.finished()

    # Get the pipe objects out of the setup objects.  This is a little bit
    # confusing, because I reuse a variable name.
    servers = server.get_pipes()
    clients = [ client.get_pipe() for client in clients ]

    identity = lambda pipe: pipe.get_identity()

    servers.sort(key=identity)
    clients.sort(key=identity)

    # Make sure that the right number of connections were made, and that the
    # server assigned valid identity numbers.
    assert len(clients) == pipes
    assert len(servers) == pipes

    for index, server in enumerate(servers):
        assert server.get_identity() == 1 + index

    for index, client in enumerate(clients):
        assert client.get_identity() == 1 + index

    # Return the newly created connections. If only one connection is being
    # created, return the pipes as simple objects rather than lists.
    if pipes == 1:
        clients = clients[0]
        servers = servers[0]

    if reverse:     return servers, clients
    else:           return clients, servers

# Disconnect {{{1
def disconnect(*pipes):
    for pipe in pipes:
        pipe.close()
# }}}1
