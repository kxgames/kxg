#!/usr/bin/env python

import random

from helpers.pipes import *
from helpers.interface import *

# Isolated Pipes {{{1
def test_isolated_pipes():
    machine, port = 'localhost', 10236

    # First, test an isolated host.
    host = PickleHost(port, identity=1)

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

    def greet_client(pipes):
        assert len(pipes) == 1
        assert pipes[0].get_identity() == 1

    def greet_server(pipe):
        assert pipe.get_identity() == 2

    server = PickleServer(port, seats=1, callback=greet_client)
    client = PickleClient(host, port, callback=greet_server)

    server.open()

    client.connect()    # Establish a connection.
    server.accept()     # Accept the connection and assign an identity.
    client.connect()    # Acknowledge the new connection.
    client.connect()    # Receive the assigned identity.

    assert server.finished()
    assert client.finished()

# Simple Messages {{{1
def test_simple_messages():
    target = 1
    host, port = 'localhost', 10236

    server = PickleServer(port, seats=1)
    client = PickleClient(host, port)

    # Setup a network connection.
    server.open()

    client.connect(); server.accept()
    client.connect(); client.connect()

    sender = client.get_pipe()
    receiver = server.get_pipes()[0]

    inbox, outbox = Inbox(), Outbox()
    sender.register(target)      

    # Send a handful of messages through the pipe.
    for index in range(5):
        message = outbox.message()
        sender.send(target, message)

    sent = sender.deliver()

    irrelevant = receiver.receive(target + 1)
    received = receiver.receive(target)

    assert not irrelevant
    assert sent == received

    for index, feedback in enumerate(receiver.receive(target)):
        tag, flavor, message = feedback
        assert tag == (1, 2, 1 + index)

    # Resend the first message received.
    tag, flavor, message = received[0]
    sender.resend(tag, message)

    sent = sender.deliver()
    received = receiver.receive(target)

    assert sent == received

    for tag, flavor, message in receiver.receive(target):
        assert tag == (1, 2, 1)

    # Close the connection.
    sender.close()
    receiver.close()

    inbox.check(outbox)

# }}}1

# Large Messages {{{1
def test_stressful_conditions(count, bytes):
    sender, receiver = connect()
    inbox, outbox = Inbox(), Outbox()

    target = 1
    received = []

    sender.register(1)

    for interation in range(count):
        message = outbox.send_message(bytes)
        sender.send(1, message)

    while sender.stream_out or receiver.stream_in:
        sender.deliver()
        for tag, flavor, message in receiver.receive(1):
            inbox.receive(message)

    disconnect(sender, receiver)
    inbox.check(outbox)

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

    sender.register(1)
    messages = [ outbox.send_message(bytes) for each in range(count) ]

    # Place the messages onto the delivery queue to create a stream.
    for message in messages:
        sender.send(1, message)

    socket = sender.socket
    stream = sender.stream_out

    # Manually deliver the stream in small chunks.
    while stream:
        size = random.choice(buffers)
        head, stream = stream[:size], stream[size:]

        socket.send(head)

        for tag, flavor, message in receiver.receive(1):
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
