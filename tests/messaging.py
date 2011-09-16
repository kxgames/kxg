#!/usr/bin/env python

import path
import threading

from messaging import Forum, Conversation

from helpers.pipes import *
from helpers.interface import *

# Forum Tests
# Setup Helper {{{1
def setup(count):
    client_pipes, server_pipes = connect(count)

    servers = [ ( Forum(*server_pipes), Inbox() ) ]
    clients = [ ( Forum(pipe), Inbox() ) for pipe in client_pipes ]

    return servers, clients

# Subscribe Helper {{{1
def subscribe(flavor, forums):
    for forum, inbox in forums:
        forum.subscribe(flavor, inbox.receive)

# Lock Helper {{{1
def lock(forums):
    for forum, inbox in forums:
        forum.lock()

# Publish Helper {{{1
def publish(outbox, forums, flavor="default"):
    for forum, inbox in forums:
        message = outbox.send_message(flavor=flavor)
        forum.publish(message)

# Deliver Helper {{{1
def deliver(servers, clients):
    for forum, inbox in clients + servers + clients:
        forum.deliver()

# Check Helper {{{1
def check(outbox, forums, shuffled=False):
    for forum, inbox in forums:
        inbox.check(outbox, shuffled)

# }}}1

# Offline Forum {{{1
def test_offline_forum():
    forum = Forum()
    inbox, outbox = Inbox(), Outbox()

    publisher = forum.get_publisher()
    subscriber = forum.get_subscriber()

    flavor = outbox.flavor()
    message = outbox.send_message()

    subscriber.subscribe(flavor, inbox.receive)
    forum.lock()

    publisher.publish(message)
    forum.deliver()

    inbox.check(outbox)

# Online Forum {{{1
def test_online_forum():
    server, clients = setup(4)

    outbox = Outbox()
    flavor = outbox.flavor()

    subscribe(flavor, clients)
    publish(outbox, server)

    lock(clients + server)

    deliver(server, clients)
    check(outbox, clients)

# }}}1

# Two Messages {{{1
def test_two_messages():
    server, clients = setup(64)

    outbox = Outbox()
    flavor = outbox.flavor()

    subscribe(flavor, clients + server)
    lock(clients + server)

    publish(outbox, server)
    publish(outbox, server)

    deliver(server, clients)
    check(outbox, clients + server)

# Shuffled Messages {{{1
def test_shuffled_messages():
    server, clients = setup(4)

    outbox = Outbox()
    flavor = outbox.flavor()

    subscribe(flavor, clients + server)
    lock(clients + server)

    for iteration in range(16):
        publish(outbox, clients)

    deliver(server, clients)
    check(outbox, clients + server, shuffled=True)

# Unrelated Messages {{{1
def test_unrelated_messages():
    server, clients = setup(4)

    outbox = Outbox()
    related = outbox.flavor("first")
    unrelated = outbox.flavor("second")

    subscribe(related, clients + server)    # Related.
    lock(clients + server)

    for iteration in range(4):
        publish(outbox, clients, "second")    # Unrelated.

    deliver(server, clients)

    # No messages should be received.
    outbox = Outbox()
    check(outbox, clients + server)

# Different Messages {{{1
def test_different_messages():
    server, clients = setup(8)
    groups = clients[:4], clients[4:]

    flavors = "first", "second"
    outboxes = Outbox(), Outbox()

    for group, outbox, flavor in zip(groups, outboxes, flavors):
        subscribe(outbox.flavor(flavor), group)

    lock(server + clients)

    for outbox, flavor in zip(outboxes, flavors):
        publish(outbox, server, flavor)

    deliver(server, clients)

    for outbox, group in zip(outboxes, groups):
        check(outbox, group)

# }}}1

# Looped Topology {{{1
def test_looped_topology():
    client_pipes, server_pipes = connect(3)

    # Group the pipes to recreate a triangular arrangement of hosts.
    pipes = [ (server_pipes[0], server_pipes[1]),
              (server_pipes[2], client_pipes[0]),
              (client_pipes[1], client_pipes[2]) ]

    # Assign each host a unique, nonzero identity number.
    for identity, peers in enumerate(pipes):
        peers[0].identity = identity + 1
        peers[1].identity = identity + 1

    # Create a forum for each host, and arbitrarily make one the "sender".
    forums = [ (Forum(*pipes[0]), Inbox()),
               (Forum(*pipes[1]), Inbox()),
               (Forum(*pipes[2]), Inbox()) ] 

    sender = [forums[0]]

    outbox = Outbox()
    flavor = outbox.flavor()

    # Have the sender publish just one message.
    subscribe(flavor, forums)
    publish(outbox, sender)
    lock(forums)

    # Update all the forums a number of times, and make sure the message is
    # only received once.
    for forum, inbox in 3 * forums:
        forum.deliver()

    check(outbox, forums)

# }}}1

# Conversation Tests
# Coming soon... {{{1
def test_conversation():
    pass

# }}}1

if __name__ == '__main__':

    with TestInterface("Testing the forums...", 7) as status:
        status.update();        test_offline_forum()
        status.update();        test_online_forum()

        status.update();        test_two_messages()
        status.update();        test_shuffled_messages()
        status.update();        test_unrelated_messages()
        status.update();        test_different_messages()

        status.update();        test_looped_topology()

    with TestInterface("Testing the conversations...", 1) as status:
        status.update();        test_conversation()

    TestInterface.report_success()

