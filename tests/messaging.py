#!/usr/bin/env python

import path, threading, testing

from messaging import *
from helpers.pipes import *

forum = testing.Suite("Testing the forums...")
conversation = testing.Suite("Testing the conversations...")
facade = testing.Suite("Testing requests and responses...")

# The forum tests are something of a mess.  I just finished making a very
# simple change to the forum class that broke a lot of the tests, and it took
# me a long time to get the tests working again.  Most of that time was spent
# either trying to figure out how the tests were supposed to work or how to fit
# a simple change into the rigid existing scaffold.  

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

# Update Helper {{{1
def update(servers, clients):
    for forum, inbox in clients + servers + clients:
        forum.update()

# Check Helper {{{1
def check(outbox, forums, shuffled=False, empty=False):
    for forum, inbox in forums:
        inbox.check(outbox, shuffled, empty)

# }}}1

# Offline Forum {{{1
@forum.test
def test_offline_forum(helper):
    forum = Forum()
    inbox, outbox = Inbox(), Outbox()

    publisher = forum.get_publisher()
    subscriber = forum.get_subscriber()

    flavor = outbox.flavor()
    message = outbox.send_message()

    subscriber.subscribe(flavor, inbox.receive)
    forum.lock()

    publisher.publish(message)
    forum.update()

    inbox.check(outbox)

# Online Forum {{{1
@forum.test
def test_online_forum(helper):
    server, clients = setup(4)

    outbox = Outbox()
    flavor = outbox.flavor()

    subscribe(flavor, clients)
    publish(outbox, server)

    lock(clients + server)

    update(server, clients)
    check(outbox, clients)

# }}}1

# Two Messages {{{1
@forum.test
def test_two_messages(helper):
    server, clients = setup(2)

    outbox = Outbox()
    flavor = outbox.flavor()

    subscribe(flavor, clients + server)
    lock(clients + server)

    publish(outbox, server)
    publish(outbox, server)

    update(server, clients)
    update(server, clients)

    check(outbox, clients + server)

# Shuffled Messages {{{1
@forum.test
def test_shuffled_messages(helper):
    server, clients = setup(4)

    outbox = Outbox()
    flavor = outbox.flavor()

    subscribe(flavor, clients + server)
    lock(clients + server)

    for iteration in range(16):
        publish(outbox, clients)

    for iteration in range(4 * 16):
        update(server, clients)

    check(outbox, clients + server, shuffled=True)

# Unrelated Messages {{{1
@forum.test
def test_unrelated_messages(helper):
    server, clients = setup(4)

    outbox = Outbox()
    related = outbox.flavor("first")
    unrelated = outbox.flavor("second")

    subscribe(related, clients + server)    # Related.
    lock(clients + server)

    for iteration in range(4):
        publish(outbox, clients, "second")    # Unrelated.

    for iteration in range(4):
        update(server, clients)

    # No messages should be received.
    outbox = Outbox()
    check(outbox, clients + server, empty=True)

# Different Messages {{{1
@forum.test
def test_different_messages(helper):
    server, clients = setup(8)
    groups = clients[:4], clients[4:]

    flavors = "first", "second"
    outboxes = Outbox(), Outbox()

    for group, outbox, flavor in zip(groups, outboxes, flavors):
        subscribe(outbox.flavor(flavor), group)

    lock(server + clients)

    for outbox, flavor in zip(outboxes, flavors):
        publish(outbox, server, flavor)

    for flavor in flavors:
        update(server, clients)

    for outbox, group in zip(outboxes, groups):
        check(outbox, group)

# }}}1

# Conversation Tests
# Setup Function {{{1
@conversation.setup
def conversation_setup(helper):
    helper.pipes = client, server = connect()

    helper.client = Conversation(client)
    helper.server = Conversation(server)
    helper.conversations = helper.client, helper.server

    helper.inbox = Inbox()
    helper.outbox = Outbox()
    helper.boxes = helper.inbox, helper.outbox

    helper.message = helper.outbox.message()
    helper.flavor = helper.outbox.flavor()
    helper.outgoing = helper.message, helper.flavor

    helper.finish = Finish()

    def setup(*exchanges):
        iterator = zip(helper.conversations, exchanges)
        for conversation, exchange in iterator:
            conversation.setup(exchange)

    def run(*exchanges):
        helper.setup(*exchanges)
        list = helper.conversations

        for conversation in list:
            conversation.start()

        while list:
            list = [ conversation for conversation in list
                    if not conversation.finished() ]

            for conversation in list:
                conversation.update()

    def check(inbox=helper.inbox, outbox=helper.outbox,
            shuffled=False, empty=False):
        inbox.check(outbox, shuffled, empty)

    helper.setup = setup
    helper.run = run
    helper.check = check

# Teardown Function {{{1
@conversation.teardown
def conversation_teardown(helper):
    disconnect(*helper.pipes)

# }}}1

# One Message {{{1
@conversation.test
def one_message(helper):
    inbox, outbox = helper.boxes
    message, flavor = helper.outgoing

    request = Send(message)
    request.transition(helper.finish)

    reply = Receive()
    reply.transition(helper.finish, flavor, inbox.receive)

    outbox.send(message)

    helper.run(request, reply)
    helper.check()

# Two Messages {{{1
@conversation.test
def two_messages(helper):
    inbox, outbox = helper.boxes
    message, flavor = helper.outgoing

    request_1 = Send(message)
    request_2 = Send(message)

    request_1.transition(request_2)
    request_2.transition(helper.finish)

    reply_1 = Receive()
    reply_2 = Receive()

    reply_1.transition(reply_2, flavor, inbox.receive)
    reply_2.transition(helper.finish, flavor, inbox.receive)

    outbox.send(message)
    outbox.send(message)

    helper.run(request_1, reply_1)
    helper.check()

# Ignore Extra Messages {{{1
@conversation.test
def ignore_extra_messages(helper):
    inbox, outbox = helper.boxes
    message, flavor = helper.outgoing

    # This setup will cause the same request to be sent twice, because the
    # first request transitions into the second one.  However, only one message
    # should be received because only one message is being listened for.

    request_1 = Send(message)
    request_2 = Send(message)

    request_1.transition(request_2)
    request_2.transition(helper.finish)

    only_reply = Receive()
    only_reply.transition(helper.finish, flavor, inbox.receive)

    outbox.send(message)

    helper.run(request_1, only_reply)
    helper.check()

# Simultaneous Exchanges {{{1
@conversation.test
def simultaneous_exchanges(helper):
    inbox, outbox = helper.boxes
    message, flavor = helper.outgoing

    # In this test, both the client and the server are simultaneously sending
    # and receiving messages of the same type.  Each side sends only one
    # message, but I expect to end up with two messages because I am sharing
    # the inbox.

    client_request, server_request = Send(message), Send(message)
    client_reply, server_reply = Receive(), Receive()

    client_request.transition(helper.finish)
    server_request.transition(helper.finish)

    client_reply.transition(helper.finish, flavor, inbox.receive)
    server_reply.transition(helper.finish, flavor, inbox.receive)

    outbox.send(message)
    outbox.send(message)

    helper.setup(client_request, server_request)
    helper.setup(client_reply, server_reply)

    helper.run()
    helper.check()

# }}}1

# Request/Response Tests
# Setup Function {{{1
@facade.setup
def facade_setup(helper):
    client, server = helper.pipes = connect()
    outbox = Outbox()

    request_message = outbox.message(flavor="first")
    request_flavor = outbox.flavor(flavor="first")

    accept_message = outbox.message(flavor="second")
    accept_flavor = outbox.flavor(flavor="second")

    reject_message = outbox.message(flavor="third")
    reject_flavor = outbox.flavor(flavor="third")

    print "Request Message:", request_message
    print "Accept Message:", accept_message
    print "Reject Message:", reject_message
    print

    class decision_callback(object):

        def __init__(self, pattern):
            self.pattern = list(pattern)

        def __str__(self):
            decision = "accept" if self.pattern[0] else "reject"
            return "Deciding to %s message.\n" % decision

        def __call__(self, message):
            print self
            return self.pattern.pop(0)

    def request():
        request = FullRequest(client,
                request_message, accept_flavor, reject_flavor)

        request.start()
        return request

    def response(*pattern):
        assert pattern
        helper.expected = pattern

        response = FullResponse(server,
                decision_callback(pattern), accept_message, reject_message)

        response.start()
        return response

    def update(request, response):
        while not request.finished():
            for conversation in (request, response):
                if not conversation.finished():
                    conversation.update()

    def finished(request, response):
        for conversation in (request, response):
            if not conversation.finished():
                return False
            return True

    def check(request, response, accepted=True):
        if accepted:
            assert request.get_accepted() == True
            assert request.get_rejected() == False

            assert request.get_response() == accept_message
            assert response.get_request() == request_message

        else:
            assert request.get_rejected() == True
            assert request.get_accepted() == False
            assert request.get_response() == reject_message

    helper.request = request
    helper.response = response

    helper.update = update
    helper.finished = finished
    helper.check = check

# Teardown Function {{{1
@facade.teardown
def facade_teardown(helper):
    disconnect(*helper.pipes)

# }}}1

# Accept Request {{{1
@facade.test
def accept_request(helper):
    request = helper.request()
    response = helper.response(True)

    helper.update(request, response)
    helper.check(request, response)

# Reject Request {{{1
@facade.test
def reject_request(helper):
    request = helper.request()
    response = helper.response(False, False, True)

    # The response() factory function copies the pattern of expected results
    # into the 'expected' variable, so that loops like this are possible.

    for expected in helper.expected:
        helper.update(request, response)
        helper.check(request, response, expected)

        if not expected:
            request = helper.request()

# }}}1

testing.run(forum, conversation, facade)
