#!/usr/bin/env python

import path
import threading

from message import Message
from messaging import Broker

broker = Broker()
message = Message()

broker.subscribe(Message, Message.receive)
broker.publish(message); Message.send()

broker.deliver()

Message.check()
Message.clear()


