#!/usr/bin/env python

import path
import threading

from messaging import Broker

from helpers.pipes import *
from helpers.interface import *

# Basic Broker {{{1
def test_basic_broker():
    broker = Broker()
    message = Message()

    broker.subscribe(Message, Message.receive)
    broker.lock()

    broker.publish(message); Message.send(message)
    broker.deliver()

    Message.check()
    Message.clear()

# Networked Broker {{{1
def test_networked_broker():
    client_pipe, server_pipe = connect()

    messages = [ Message(), Message() ]
    brokers = [ Broker(client_pipe), Broker(server_pipe) ]

    for broker in brokers:
        broker.subscribe(Message, Message.receive)
        broker.lock()

    for broker, message in zip(brokers, messages):
        broker.publish(message)
        
    for iteration in range(2):
        for message in messages:
            Message.send(message)

        for broker in brokers:
            broker.deliver()

    finish(client_pipe, server_pipe)

# }}}1

if __name__ == '__main__':

    with TestInterface("Testing the broker...", 2) as status:
        status.update();        test_basic_broker()
        status.update();        test_networked_broker()

    TestInterface.report_success()

