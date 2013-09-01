#!/usr/bin/env python

import engine
import pprint

logger = engine.MultiplayerDebugger.Logger('Kale', True)

token = engine.Token()

with logger:
    pprint.pprint(dir(token))
