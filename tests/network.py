#!/usr/bin/env python

import random

from helpers.pipes import *
from helpers.interface import *

# Isolated Pipes {{{1
def test_isolated_pipes():
    machine, port = 'localhost', 10236

    # First, test an isolated host.
    host = PickleHost(port)

    # None of these commands should fail, even though there is no client.
    host.open()
    host.accept(); host.accept()
    host.close()

    # Once the host is closed, accept() should raise an assertion.
    try: host.accept()
    except AssertionError: pass
    else: raise AssertionError

    # Now test an isolated client.
    client = PickleClient(machine, port, identity=1)

    client.connect()
    client.connect()

    assert not client.finished()

# Connected Pipes {{{1
def test_connected_pipes():
    host, port = 'localhost', 10236

    def check_client(pipe):
        assert pipe.get_identity() == 1

    def check_server(pipes):
        assert len(pipes) == 1
        assert pipes[0].get_identity() == 1

    server = PickleServer(port, seats=1, callback=check_server)
    client = PickleClient(host, port, callback=check_client)

    server.open()

    client.connect()    # Establish a connection.
    server.accept()     # Accept the connection and assign an identity.
    client.connect()    # Acknowledge the new connection.
    client.connect()    # Receive the assigned identity.

    assert server.finished()
    assert client.finished()

# Simple Messages {{{1
def test_simple_messages():
    host, port = 'localhost', 10236

    server = PickleServer(port, seats=1)
    client = PickleClient(host, port)

    # Setup a network connection.
    server.open()

    client.connect(); server.accept()
    client.connect(); client.connect()

    sender = client.get_pipe()
    receiver = server.get_pipes()[0]

    sender.lock()
    receiver.lock()

    # Send a handful of messages through the pipe.
    for index in range(5):
        message = Message()
        sender.send(message)

    sent = sender.deliver()
    received = receiver.receive()

    assert sent == received

    # Close the connection.
    sender.close()
    receiver.close()

# }}}1

# Large Messages {{{1
def test_stressful_conditions(count, bytes):
    sender, receiver = connect()
    outbox, delivered, received = Outbox(), Inbox(), Inbox()

    sender.lock(); receiver.lock()

    for iteration in range(count):
        message = outbox.send_message(bytes)
        sender.send(message)

    while sender.stream_out or receiver.stream_in:

        for message in sender.deliver():
            delivered.receive(message)

        for message in receiver.receive():
            received.receive(message)

    disconnect(sender, receiver)

    delivered.check(outbox)
    received.check(outbox)

def test_many_messages():
    test_stressful_conditions(count=2**12, bytes=2**4)

def test_large_messages():
    test_stressful_conditions(count=2**4, bytes=2**17)

# Partial Messages {{{1
def test_partial_messages():
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
    stream = sender.stream_out

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

# }}}1

if __name__ == '__main__':

    with TestInterface("Performing simple tests...", 3) as status:
        status.update();        test_isolated_pipes()
        status.update();        test_connected_pipes()
        status.update();        test_simple_messages()

    with TestInterface("Performing rigorous tests...", 3) as status:
        status.update();        test_many_messages()
        status.update();        test_large_messages()
        status.update();        test_partial_messages()

    TestInterface.report_success()
