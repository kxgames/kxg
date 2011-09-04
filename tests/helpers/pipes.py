# This path module tweaks sys.path and needs to be called before any module
# from this package is imported.

import os, path
import struct

from network import EasyServer, EasyClient

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
    machine, port = 'localhost', 10236

    # The easy clients are the most generally useful.
    host = EasyServer(machine, port, pipes, integrate=integrate)
    clients = [ EasyClient(machine, port, integrate) for each in range(pipes) ]

    host.setup();   assert host.empty()

    # Each client's setup() method needs to be called at least twice.
    for client in clients:
        client.setup(); assert not client.ready()
        client.setup(); assert client.ready()

        host.accept();  assert not host.empty()

    assert host.full()
    servers = host.members()

    for pipe in servers + clients:
        pipe.update()

    for server in servers:
        assert server.ready()
        assert server.identify() == 1

    for index, client in enumerate(clients):
        assert client.identify() == 2 + index

    assert len(clients) == pipes
    assert len(servers) == pipes

    # If only one connection is being created, don't return lists.
    if pipes == 1:
        clients = clients[0]
        servers = servers[0]

    if reverse:     return servers, clients
    else:           return clients, servers

# Update {{{1
def update(*pipes):
    remaining = []
    if not pipes: return

    for pipe in pipes:
        pipe.deliver()

    for pipe in pipes:
        pipe.receive()

    for pipe in pipes:
        if pipe.stream_out or pipe.stream_in:
            remaining.append(pipe)

    update(*remaining)

# Disconnect {{{1
def disconnect(*pipes):
    for pipe in pipes:
        pipe.teardown()
# }}}1

