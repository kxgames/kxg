#!/usr/bin/env python

import kxg, knockout
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('first_name')
parser.add_argument('second_name')
parser.add_argument('--port', '-p', default=53351, type=int)

arguments = parser.parse_args()
names = arguments.first_name.title(), arguments.second_name.title()
host, port = 'localhost', arguments.port

debugger = kxg.MultiplayerDebugger()

debugger.loop("Server", knockout.ServerLoop(host, port))
debugger.loop("Client-" + names[0], knockout.ClientLoop(names[0], host, port))
debugger.loop("Client-" + names[1], knockout.ClientLoop(names[1], host, port))

debugger.run()
