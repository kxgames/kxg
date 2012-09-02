""" This script allows python to find all the modules contained in this package.
By default, python looks for modules in the same directory as this as this
script.  Although this approach usually makes sense, it doesn't work for this
package since the code is kept in a subdirectory.  By changing the __path__
variable, python knows to look in the proper subdirectory. """

import os

# Tell python where to look for modules.
repository = __path__[0]
__path__[0] = os.path.join(repository, "modules")

# Delete the two local variables that were created.
del os, repository

# Expose all of the modules included in this package.
import engine
import geometry, sprites, keychain
import network, messaging
import pygame_maps

# Import a few of the most useful classes into the top-level namespace.
from engine import *

del RemoteActor, Mailbox, LocalMailbox, RemoteMailbox
del TokenProxy, ProxyLock, ProtectedProxyLock, UnprotectedProxyLock
