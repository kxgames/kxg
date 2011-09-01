#!/usr/bin/env python

import random

from helpers.pipes import *
from helpers.interface import *

# Simple Tests {{{1
def test_one_message():
    client, server = connect()
    message = Message()

    client.outgoing(Message, Message.send)
    server.incoming(Message, Message.receive)

    client.queue(message)

    update(client, server)
    finish(client, server)

def test_two_messages():
    forward = connect(reverse=False)
    reverse = connect(reverse=True)

    messages = Message(), Message()

    # Try sending from both the client and the host ends.
    for sender, receiver in forward, reverse:
        sender.outgoing(Message, Message.send)
        receiver.incoming(Message, Message.receive)

        # Try adding more than one callback.
        sender.outgoing(Message, lambda client, message: None)
        receiver.incoming(Message, lambda client, message: None)

        for message in messages:
            sender.queue(message)

        update(sender, receiver)
        finish(sender, receiver)

def test_default_callbacks():
    client, server = connect()
    message = Message()

    client.default_outgoing(Message.send)
    server.default_incoming(Message.receive)

    try: server.queue(message)
    except AssertionError: pass
    else: raise AssertionError

    client.queue(message)

    update(client, server)
    finish(client, server)

def test_missing_callbacks():
    client, server = connect()
    message = Message(10)

    # Make sure messages cannot be sent before they are registered.
    try: client.queue(message)
    except AssertionError: pass
    else: raise AssertionError

    try: server.queue(message)
    except AssertionError: pass
    else: raise AssertionError

    # Now register this type of message so it can be sent.
    client.outgoing(Message)
    server.outgoing(Message)

    client.queue(message)
    server.queue(message)

    client.deliver()
    server.deliver()

    # Make sure unregistered messages cannot be received, even if the same type
    # of message is registered to be sent.
    try: server.receive()
    except AssertionError: pass
    else: raise AssertionError

    try: client.receive()
    except AssertionError: pass
    else: raise AssertionError

# Rigorous Tests {{{1
def test_variable_conditions(count=0, bytes=0):
    client, server = connect()
    messages = [ Message(bytes) for index in range(count) ]

    client.outgoing(Message, Message.send)
    server.incoming(Message, Message.receive)

    for message in messages:
        client.queue(message)

    # Continue updating until the client has emptied its outgoing stream.
    while client.stream_out:
        update(client, server)

    finish(client, server)

def test_many_messages():
    test_variable_conditions(count=2**12, bytes=2**8)

def test_large_messages():
    test_variable_conditions(count=2**7, bytes=2**17)

def test_partial_messages(count=2**8, bytes=2**8):
    client, server = connect()

    buffers = range(2 * bytes)
    messages = [ Message(bytes) for index in range(count) ]

    client.outgoing(Message, Message.send)
    server.incoming(Message, Message.receive)

    # Place the messages onto the delivery queue to create a stream.
    for message in messages:
        client.queue(message)

    socket = client.socket
    stream = client.stream_out

    # Manually deliver the stream in small chunks.
    while stream:
        size = random.choice(buffers)
        head, stream = stream[:size], stream[size:]

        socket.send(head)
        server.receive()
    
    # Make sure all the messages were properly received.
    finish(client, server)

# }}}1

if __name__ == '__main__':

    with TestInterface("Performing simple tests...", 4) as status:
        status.update();        test_one_message()
        status.update();        test_two_messages()
        status.update();        test_default_callbacks()
        status.update();        test_missing_callbacks()

    with TestInterface("Performing rigorous tests...", 3) as status:
        status.update();        test_many_messages()
        status.update();        test_large_messages()
        status.update();        test_partial_messages()

    TestInterface.report_success()
