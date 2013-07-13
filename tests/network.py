#!/usr/bin/env python

import random
import testing

from helpers.pipes import *

class Token (object):

    def __init__(self, id, partner=None):
        self.id = id
        self.partner = partner

    def __str__(self):
        string = '<Token addr=0x%x id=%d' % (id(self), self.id)
        if self.partner: string += ' partner=%d' % self.partner.id
        string += '>'
        return string

    __repr__ = __str__

    def __eq__(self, other):
        return self.id == other.id and self.partner == other.partner


class Serializer (object):

    def __init__(self, world):
        self.world = world

    def pack(self, message):
        from pickle import Pickler
        from cStringIO import StringIO

        buffer = StringIO()
        delegate = Pickler(buffer)

        delegate.persistent_id = self.persistent_id
        delegate.dump(message)

        return buffer.getvalue()

    def unpack(self, packet):
        from pickle import Unpickler
        from cStringIO import StringIO

        buffer = StringIO(packet)
        delegate = Unpickler(buffer)

        delegate.persistent_load = self.persistent_load
        return delegate.load()

    def persistent_id(self, token):
        if isinstance(token, Token):
            if token.id in self.world:
                return token.id

    def persistent_load(self, id):
        return self.world[int(id)]



@testing.test
def isolated_pipes(helper):
    machine, port = 'localhost', 10236

    # First, test an isolated host.
    host = Host(machine, port)

    # None of these commands should fail, even though there is no client.
    host.open()
    host.accept(); host.accept()
    host.close()

    # Once the host is closed, accept() should raise an assertion.
    try: host.accept()
    except AssertionError: pass
    else: raise AssertionError

    # Now test an isolated client.
    client = Client(machine, port)

    client.connect()
    client.connect()

    assert not client.finished()

@testing.test
def connected_pipes(helper):
    host, port = 'localhost', 10236

    def check_client(pipe):
        pass

    def check_server(pipes):
        assert len(pipes) == 1


    server = Server(host, port, seats=1, callback=check_server)
    client = Client(host, port, callback=check_client)

    server.open()

    client.connect()    # Establish a connection.
    server.accept()     # Accept the connection.
    client.connect()    # Acknowledge the new connection.

    assert server.finished()
    assert client.finished()

@testing.test
def simple_messages(helper):
    host, port = 'localhost', 10236

    server = Server(host, port, seats=1)
    client = Client(host, port)

    # Setup a network connection.
    server.open()

    client.connect()
    server.accept()
    client.connect()

    sender = client.get_pipe()
    receiver = server.get_pipes()[0]

    sender.lock()
    receiver.lock()

    # Send a handful of messages through the pipe.
    for index in range(5):
        message = Message()
        sender.send(message)

    sent = sender.deliver()
    received = [message for message in receiver.receive()]

    print sent, received
    assert sent == received

    # Close the connection.
    assert not sender.finished()
    sender.close()
    assert sender.finished()

    assert not receiver.finished()
    received = [message for message in receiver.receive()]
    assert receiver.finished()


@testing.test
def test_many_messages(helper):
    test_stressful_conditions(count=2**12, bytes=2**5)

@testing.test
def test_large_messages(helper):
    test_stressful_conditions(count=2**5, bytes=2**18)

def test_stressful_conditions(count, bytes):
    sender, receiver = connect()
    outbox, delivered, received = Outbox(), Inbox(), Inbox()

    sender.lock(); receiver.lock()

    for iteration in range(count):
        message = outbox.send_message(bytes)
        sender.send(message)

    while sender.busy() or receiver.busy():
        for message in sender.deliver():
            delivered.receive(message)

        for message in receiver.receive():
            received.receive(message)

    disconnect(sender, receiver)

    delivered.check(outbox)
    received.check(outbox)

@testing.test
def test_partial_messages(helper):
    sender, receiver = connect()
    inbox, outbox = Inbox(), Outbox()

    count = bytes = 2**8
    buffers = range(2 * bytes)

    sender.lock(); receiver.lock()

    messages = [ outbox.send_message(bytes) for each in range(count) ]

    # Place the messages onto the delivery queue to create a stream.
    for message in messages:
        sender.send(message)

    socket = sender.socket
    stream = ''.join([ package[0] for package in sender.outgoing])

    # Manually deliver the stream in small chunks.
    while stream:
        size = random.choice(buffers)
        head, stream = stream[:size], stream[size:]

        socket.send(head)

        for message in receiver.receive():
            inbox.receive(message)
    
    # Make sure all the messages were properly received.
    disconnect(sender, receiver)
    inbox.check(outbox)

@testing.test
def test_token_serialization(helper):
    """ Test the situation where two messages are sent, and the second one 
    can't be unpacked until the first one is processed.  This situation comes 
    up fairly often in games.  It requires that pipe.receive() returns messages 
    as an iterator, so that each message can be processed in turn. """

    sender, receiver = connect()
    sender.lock(); receiver.lock()

    # Send the messages.
    world = {}
    sender.set_serializer(Serializer(world))

    first_token = Token(1)
    second_token = Token(2, first_token)

    for token in (first_token, second_token):
        sender.send(token)
        world[token.id] = token

    sender.deliver()
    sender.close()

    # Receive the messages.
    world = {}
    receiver.set_serializer(Serializer(world))

    for token in receiver.receive():
        world[token.id] = token

    # Check the results.
    assert world[1] == first_token
    assert world[2] == second_token
    assert world[2].partner is world[1]


testing.title("Testing the network module...")
testing.run()

