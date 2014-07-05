#!/usr/bin/env python

from __future__ import division
import path, testing, contextlib
from kxg.events import *

def make_note(message):
    make_note.messages.append(message)
    print message

@contextlib.contextmanager
def record_notes():
    make_note.messages = []
    yield make_note.messages


class ParentPublisher (Dispatcher):

    def parent_event(self, message):
        self.notify('on_parent_event', message)

    @event
    def on_parent_event(self, message):
        make_note('ParentPublisher.on_parent_event({})'.format(message))


class ChildPublisher (ParentPublisher):

    def child_event(self, message):
        self.notify('on_child_event', message)

    @event
    def on_child_event(self, message):
        make_note('ChildPublisher.on_child_event({})'.format(message))


class Handler:

    def on_parent_event(self, message):
        make_note('Handler.on_parent_event({})'.format(message))

    def on_child_event(self, message):
        make_note('Handler.on_child_event({})'.format(message))

    def irrelevant_method(self):
        pass



@testing.test
def test_handler_function():
    def handler(message):
        make_note("handler({})".format(message))

    with record_notes() as notes:
        publisher = ParentPublisher()
        publisher.connect(on_parent_event=handler)
        publisher.parent_event('hello')
        publisher.disconnect(handler)
        publisher.parent_event('goodbye')

    assert len(notes) == 3
    assert notes[0] == 'ParentPublisher.on_parent_event(hello)'
    assert notes[1] == 'handler(hello)'
    assert notes[2] == 'ParentPublisher.on_parent_event(goodbye)'

@testing.test
def test_handler_lambda_function():
    handler = lambda message: make_note('lambda({})'.format(message))

    with record_notes() as notes:
        publisher = ParentPublisher()
        publisher.connect(on_parent_event=handler)
        publisher.parent_event('hello')
        publisher.disconnect(handler)
        publisher.parent_event('goodbye')

    assert len(notes) == 3
    assert notes[0] == 'ParentPublisher.on_parent_event(hello)'
    assert notes[1] == 'lambda(hello)'
    assert notes[2] == 'ParentPublisher.on_parent_event(goodbye)'

@testing.test
def test_handler_object():
    with record_notes() as notes:
        publisher = ParentPublisher()
        handler = Handler()

        publisher.connect(handler)
        publisher.parent_event('hello')
        publisher.disconnect(handler)
        publisher.parent_event('goodbye')

    assert len(notes) == 3
    assert notes[0] == 'ParentPublisher.on_parent_event(hello)'
    assert notes[1] == 'Handler.on_parent_event(hello)'
    assert notes[2] == 'ParentPublisher.on_parent_event(goodbye)'

@testing.test
def test_inherited_events():
    with record_notes() as notes:
        publisher = ChildPublisher()
        handler = Handler()

        publisher.connect(handler)
        publisher.parent_event('hello')
        publisher.child_event('bonjour')

    assert len(notes) == 4
    assert notes[0] == 'ParentPublisher.on_parent_event(hello)'
    assert notes[1] == 'Handler.on_parent_event(hello)'
    assert notes[2] == 'ChildPublisher.on_child_event(bonjour)'
    assert notes[3] == 'Handler.on_child_event(bonjour)'


@testing.skip
def test_event_validation():
    pass

@testing.test
def test_docstrings():

    class DocumentedPublisher (Dispatcher):
        """ 
        DocumentedPublisher
        
        {events}

        After events...
        """

        @event
        def on_first_event(self):
            """ Called when the first kind of event happens. """
            pass

        @event
        def on_second_event(self):
            """ Called when the second kind of event happens.  This different
            from the first kind of event, because it happens second. """
            pass

    class NoEvents (Dispatcher):
        """ 
        NoEvents

        {events}

        After events...
        """
        pass

    class Blah (Dispatcher):
        """ 
        Normal doctring, no formatting key.
        """


    print DocumentedPublisher.__doc__
    print NoEvents.__doc__
    print Blah.__doc__
    raise NotImplementedError




testing.title("Testing the events module...")
testing.run()

