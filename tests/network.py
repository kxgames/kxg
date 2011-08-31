#!/usr/bin/env python

import sys
import random

# This module tweaks sys.path and needs to be called before any module from
# this package is imported.
import path
import network, message

# Message {{{1
class Message(message.Message):

    @classmethod
    def send(cls, client, message):
        cls.outgoing.append(message)

    @classmethod
    def receive(cls, client, message):
        cls.incoming.append(message)

# }}}1

# Connect {{{1
def connect(reverse=False):

    # These test are specifically for the pickle client.
    greeter = network.PickleHost('localhost', 11236)
    client = network.PickleClient('localhost', 11236)

    greeter.setup()

    # The client's setup() method needs to be called at least twice.
    client.setup(); assert not client.ready()
    client.setup(); assert client.ready()

    servers = greeter.accept()
    server = servers[0]

    assert len(servers) == 1
    assert server.ready()

    if reversed:    return server, client
    else:           return client, server

# Update {{{1
def update(*pipes):
    for pipe in pipes:
        pipe.deliver()

    for pipe in pipes:
        pipe.receive()

# Finish {{{1
def finish(*pipes):
    for pipe in pipes:
        pipe.teardown()

    Message.check()
    Message.clear()

# }}}1

# Simple Tests {{{1
def test_one_message(bytes=8):
    client, server = connect()
    message = Message(bytes)

    client.outgoing(Message, Message.send)
    server.incoming(Message, Message.receive)

    client.queue(message)

    update(client, server)
    finish(client, server)

def test_two_messages(bytes=8):
    forward = connect(reverse=False)
    reverse = connect(reverse=True)

    messages = Message(bytes), Message(bytes)

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

def test_error_cases():
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

    # Status Display {{{1
    def update_status(current, total):
        backspace = '\b'
        status = '(%d/%d)' % (current, total)

        sys.stdout.write(backspace * len(status))
        sys.stdout.write(status)
        sys.stdout.flush()
    # }}}1

    print "Performing simple tests... (x/x)",
    update_status(1, 3);        test_one_message()
    update_status(2, 3);        test_two_messages()
    update_status(3, 3);        test_error_cases()
    print

    print "Performing rigorous tests... (x/x)",
    update_status(1, 3);        test_many_messages()
    update_status(2, 3);        test_large_messages()
    update_status(3, 3);        test_partial_messages()
    print
    
    print "All tests passed."
