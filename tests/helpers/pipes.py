# This path module tweaks sys.path and needs to be called before any module
# from this package is imported.

import os, struct
import path, network

# Message Class {{{1
class Message(object):

    outgoing = []
    incoming = []

    def __init__(self, bytes=8):
        self.data = os.urandom(bytes)

    def __repr__(self):
        format = "H"    # Unsigned short
        length = struct.calcsize(format)

        integer = struct.unpack(format, self.data[:length])[0]
        return str(integer)

    def __eq__(self, other):
        return self.data == other.data

    @classmethod
    def send(cls, *arguments):
        message = arguments[-1];
        cls.outgoing.append(message)

    @classmethod
    def receive(cls, *arguments):
        message = arguments[-1]
        cls.incoming.append(message)

    @classmethod
    def check(cls):
        incoming_count = len(cls.incoming)
        outgoing_count = len(cls.outgoing)

        feedback = "%d in, %d out." % (incoming_count, outgoing_count)
        assert incoming_count == outgoing_count, feedback

        messages = zip(cls.outgoing, cls.incoming)

        for sent, received in messages:
            feedback = "'%s' sent, '%s' received." % (sent, received)
            assert sent == received, feedback

    @classmethod
    def clear(cls):
        cls.outgoing = []
        cls.incoming = []

# Extra Message Classes {{{1
class FirstMessage(Message): pass
class SecondMessage(Message): pass
# }}}1

# Connect Helper {{{1
def connect(reverse=False):

    # These test are specifically for the pickle client.
    host = network.PickleHost('localhost', 10236)
    client = network.PickleClient('localhost', 10236)

    host.setup()

    # The client's setup() method needs to be called at least twice.
    client.setup(); assert not client.ready()
    client.setup(); assert client.ready()

    servers = host.accept()
    server = servers[0]

    assert len(servers) == 1
    assert server.ready()

    if reversed:    return server, client
    else:           return client, server

# Update Helper {{{1
def update(*pipes):
    for pipe in pipes:
        pipe.deliver()

    for pipe in pipes:
        pipe.receive()

# Finish Helper {{{1
def finish(*pipes):
    for pipe in pipes:
        pipe.teardown()

    Message.check()
    Message.clear()

# }}}1
