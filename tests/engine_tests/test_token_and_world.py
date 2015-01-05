#!/usr/bin/env python

import kxg, finalexam
from helpers import *
from pprint import pprint

@finalexam.test
def test_token_pickling():
    import pickle
    original_token = DummyToken()
    #original_token.subscribe_to_message('asdasd', 'asdsad')
    pprint(original_token.__dict__)
    print()
    buffer = pickle.dumps(original_token)
    pickled_token = pickle.loads(buffer)
    print()
    pprint(pickled_token.__dict__)
    assert False

if __name__ == '__main__':
    finalexam.title("Testing the tokens and the world...")
    finalexam.run()
