import os
import struct

class Message(object):

    outgoing = []
    incoming = []

    def __init__(self, bytes=8):
        self.data = os.urandom(bytes)

    def __repr__(self):
        format = "H"    # Unsigned short
        length = struct.calcsize(format)

        integer = struct.unpack(format, self.data[:length])[0]
        return str(integer)

    def __eq__(self, other):
        return self.data == other.data

    @classmethod
    def send(cls, message):
        cls.outgoing.append(message)

    @classmethod
    def receive(cls, message):
        cls.incoming.append(message)

    @classmethod
    def check(cls):
        messages = zip(cls.outgoing, cls.incoming)
        assert len(cls.incoming) == len(cls.outgoing)

        for sent, received in messages:
            assert sent == received

    @classmethod
    def clear(cls):
        cls.outgoing = []
        cls.incoming = []
