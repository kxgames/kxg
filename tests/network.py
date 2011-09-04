#!/usr/bin/env python

import random

from helpers.pipes import *
from helpers.interface import *

# I completely forgot to test the forgetting methods.

# Setup {{{1
def setup(integrate=lambda x: x):
    tests = {}, {}
    direction = True, False

    for test, reverse in zip(tests, direction):
        sender, receiver = connect(reverse=reverse, integrate=integrate)
        inbox, outbox = Inbox(), Outbox()

        test["sender"], test["receiver"] = sender, receiver
        test["inbox"], test["outbox"] = inbox, outbox

        flavor = outbox.flavor()

        sender.outgoing(flavor, outbox.send)
        receiver.incoming(flavor, inbox.receive)

    return tests

# Send {{{1
def send(test, bytes=8):
    sender, outbox = test["sender"], test["outbox"]

    message = outbox.message(bytes)
    old_ticker = sender.message_ticker

    sender.queue(message)

    assert sender.message_ticker == old_ticker + 1

# Receive {{{1
def receive(test):
    sender, receiver = test["sender"], test["receiver"]
    inbox, outbox = test["inbox"], test["outbox"]

    update(sender, receiver)
    disconnect(sender, receiver)

    inbox.check(outbox)

# }}}1

# Simple Tests {{{1
def test_one_message():
    for test in setup():
        send(test)
        receive(test)

def test_two_messages():
    for test in setup():
        send(test); send(test)
        receive(test)

def test_multiple_clients():
    clients, servers = connect(10)
    inbox, outbox = Inbox(), Outbox()

    flavor = outbox.flavor()
    message = outbox.message()

    for client in clients:
        client.outgoing(flavor, outbox.send)

    for server in servers:
        server.incoming(flavor, inbox.receive)

    inbox.check(outbox)

def test_defaults():
    sender, receiver = connect()
    inbox, outbox = Inbox(), Outbox()

    message = outbox.message()

    sender.outgoing_default(outbox.send)
    receiver.incoming_default(inbox.receive)

    sender.queue(message)

    update(sender, receiver)
    disconnect(sender, receiver)

    inbox.check(outbox)

def test_surprises():
    sender, receiver = connect()
    inbox, outbox = Inbox(), Outbox()

    flavor = outbox.flavor()
    message = outbox.message()

    # By default, outgoing messages must be registered.
    try: sender.queue(message)
    except AssertionError: pass
    else: raise AssertionError

    sender.outgoing(flavor)
    sender.queue(message)

    # Incoming messages also have to be registered.
    try: update(sender, receiver)
    except AssertionError: pass
    else: raise AssertionError

    receiver.incoming(flavor, lambda *ignore: None)
    sender.queue(message)

    update(sender, receiver)
    disconnect(sender, receiver)

def test_integration():

    def integrate(message):
        message.integrated = True
        return message

    for test in setup(integrate):
        send(test)
        receive(test)

        for message in test["inbox"]:
            assert hasattr(message, "integrated")

# Rigorous Tests {{{1
def test_stressful_conditions(count, bytes):
    for test in setup():
        for iteration in range(count):
            send(test, bytes)
        receive(test)

def test_many_messages():
    test_stressful_conditions(count=2**12, bytes=2**8)

def test_large_messages():
    test_stressful_conditions(count=2**7, bytes=2**17)

def test_partial_messages(count=2**8, bytes=2**8):
    client, server = connect()
    inbox, outbox = Inbox(), Outbox()

    flavor = outbox.flavor()
    messages = [ outbox.message(bytes) for index in range(count) ]

    buffers = range(2 * bytes)

    client.outgoing(flavor, outbox.send)
    server.incoming(flavor, inbox.receive)

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
    
    disconnect(client, server)

    # Make sure all the messages were properly received.
    inbox.check(outbox)

# }}}1

if __name__ == '__main__':

    with TestInterface("Performing simple tests...", 6) as status:
        status.update();        test_one_message()
        status.update();        test_two_messages()
        status.update();        test_multiple_clients()

        status.update();        test_defaults()
        status.update();        test_surprises()
        status.update();        test_integration()

    with TestInterface("Performing rigorous tests...", 3) as status:
        status.update();        test_many_messages()
        status.update();        test_large_messages()
        status.update();        test_partial_messages()

    TestInterface.report_success()
