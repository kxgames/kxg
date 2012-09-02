from __future__ import print_function

import sys
import copy

import pygame_maps

# Things to do:
#   ~ Add a universal reset key (ie. ESC). Or other universal trigger
#       keys. 
#       NOTE: a reset key is pointless... Just never register the
#       key and it will always fail, thereby resetting the chain.
#
#   ~ Add sequence objects? The Key chain would update a list of
#       sequences. Each sequence would remove themselves when they
#       execute or fail. When the list is empty, the keychain starts
#       over.
#   ~ Add exceptions for nodes. When a node is active, if a key that
#       would normally fail is entered, the node just ignores it.
#       May be useful to prevent accidental input, such as mouse
#       clicks.
#   ~ Add ghost chains. When a node activates a ghost chain, somehow
#       also activate the root. If a ghost chain fails, it does so 
#       quietly. If it executes, then reset the whole keychain?
#       Intended for use with optional information for a sequence.
#       Issue: Can create really confusing situations with different
#       chains executing simultaniously.
#   ~ Add background chains. Similar to ghost chains and exceptions.
#       They will ignore unrelated input, but will not prevent other
#       hotkey branches from running or executing. 
#   ~ Add chains with optional args. After each major key (a,b,c in
#       example), the user can enter an argument hotkey or the next
#       major key.
#       
#       a ----------> b ----------> c------------> execute()
#        \        ^    \        ^    \        ^
#        arg1 --->^    arg1 --->^    arg1 --->^
#          \      ^      \      ^      \      ^
#          arg2 ->^      arg2 ->^      arg2 ->^
#            \    ^        \    ^        \    ^
#            arg3 ^        arg3 ^        arg3 ^
#
#   ~ Add infinite argument keys. Used for entering whole words? (for
#       in game messaging?)

class KeyChain:

    def __init__ (self):

        self.active = None
        self.sequence = []
        self.root_node = None
        self.verbose = False

        self.active_lenses = []
        self.lenses = {}

    def setup (self):

        # Create an empty root Node.
        self.root_node = Node ()
        self.root_node.verbose = self.verbose
        self.root_node.setup (self, None, None, None)
        self.activate (self.root_node)

    def register_lens (self, name, lens):

        # A lens is a dictionary mapping input to input.
        #
        # A lens will only be applied if it is active and the input is
        # defined in the domain of the lens.
        # 
        # The lens will be stored in the keychain in another dictionary
        # with the name as the key.

        if self.verbose: 
            print ('Registering lens : %s' %name)

        new_lens = Lense (self, name, copy.copy(lens))
        self.lenses[name] = new_lens

    def register_chain_key (self, sequence, callback, args):

        # This event assumes all sequence members are pygame keys.

        k2s = pygame_maps.key_to_string

        new_sequence = []

        for member in sequence:
            new_sequence.append (k2s[member])

        self.register_chain (new_sequence, callback, args)

    def register_chain_mouse (self, sequence, callback, args):
        
        # This function assumes sequence members with even indices are
        # pygame event types and the odd members are pygame mouse 
        # button numbers.

        e2s = pygame_maps.event_to_string
        m2s = pygame_maps.mouse_to_string

        new_sequence = []
        even = True

        for member in sequence:
            if even:    new_sequence.append (e2s[member])
            else:       new_sequence.append (m2s[member])
            even = not even

        self.register_chain (new_sequence, callback, args)

    def register_chain (self, sequence, callback, args):

        # All objects have a built in node.select() callback. The user
        # inputted callback is added to the node's list of callbacks
        
        if self.verbose: 
            print ('Adding new sequence: ', end='')
            for member in sequence[:-1]: print ('"%s", ' %member, end='')
            else: print ('"%s"' %sequence[-1])

        node = self.root_node

        for key in sequence[:-1]:
            node = self.place_node(node, key, None, None)
        else:
            last = self.place_node (node, sequence[-1], callback, args)

        if self.verbose: print ()

    def place_node (self, parent, key, callback, args):

        if self.verbose: 
            print ('~ Attempting Key "%s"' %(key))

        if key in parent.links:

            # The link already exists.
            if self.verbose: print ('    Link already exists')
            node = parent.links[key]

            if callback != None:
                # This is a terminal node.
                if self.verbose: print ('    Link is terminal ')
                node.add_callback(callback, args)

            return node

        else:

            # If it doesn't exist, make a new node and place it in
            # the chain.
            node = Node()
            node.verbose = self.verbose

            if self.verbose: 
                print ('    Making node "%s"' %(key))
            node.setup (self, key, callback, args)

            parent.add_link (key, node)

            return node

    def handle_key (self, input, lens_only=False):

        self.handle (pygame_maps.key_to_string[input], lens_only)

    def handle_event (self, input, lens_only=False):

        self.handle (pygame_maps.event_to_string[input], lens_only)

    def handle_mouse (self, input, lens_only=False):

        self.handle (pygame_maps.mouse_to_string[input], lens_only)

    def handle (self, input, lens_only=False):

        # See if the input is really a lens.
        if input in self.lenses:

            lens = self.lenses[input]

            # Toggle the lens.
            if lens in self.active_lenses:

                #if self.verbose:
                #    print ('Deactivating the %s lens' %lens.get_name())

                self.active_lenses.remove (lens)

            else:

                #if self.verbose:
                #    print ('Activating the %s lens' %lens.get_name())

                self.active_lenses.append (lens)

        elif not lens_only:

            # For any active lenses, create the image of the input
            # through the lens.
            for lens in self.active_lenses:

                if input in lens:

                    #if self.verbose:
                    #    print ('Applying the %s lens' %lens.get_name())
                    #    print ('    %s  ->  %s' %(input, lens[input]))

                    input = lens[input]

            # Give the input to the active node.
            self.sequence.append(input)
            self.active.check(input)
    
    def activate (self, new):

        self.active = new

    def reset (self):

        self.sequence = []
        self.activate (self.root_node)


class Lense (dict):

    def __init__ (self, manager, name, map):
        dict.__init__(self, map)

        self.manager = manager
        self.name = name

    def get_name (self): 
        
        return self.name

    def get_manager (self): 
        
        return self.manager


class Node:

    def __init__ (self):

        self.manager = None
        self.key = None
        self.callbacks = []
        self.links = {}
        self.verbose = False

    def setup (self, manager, key, callback, args):

        self.manager = manager
        self.key = key
        self.add_callback(callback, args)

    def add_callback(self, callback, args):

        if callback != None:

            self.callbacks.append ((callback, args))
            if self.verbose: 
                print ('    Node callbacks:')
                for callback in self.callbacks:
                    print('      %s' %callback[0])

    def add_link (self, key, node):

        assert key not in self.links

        self.links[key] = node

    def check (self, input):

        if self.verbose: 
            print ("%s, " %input, end='')
            sys.stdout.flush()

        # If the current Node has a link that matches the input, execute
        # that link's callbacks. Otherwise, the sequence breaks.
        if input in self.links:
            self.links[input].execute()

        else:
            if self.verbose: print (' fails.')
            self.break_sequence()
    
    def execute (self):

        if len(self.links) > 0: self.select()
        else: self.manager.reset()

        if self.verbose:
            if len(self.callbacks) > 0:
                print (' OK.')
                print ('    Now calling:')

        for callback in self.callbacks:

            if self.verbose: print('      %s' %callback[0])
            args = callback[1]
            callback[0](args)

    def select (self):
        
        self.manager.activate(self)

    def break_sequence (self):

        self.manager.reset()

    def __eq__ (self, other):

        if isinstance (other, Node):
            return self.key == other.key
        else:
            try:
                return self.key == other
            except:
                return False

    def __ne__ (self, other):

        return not self.__eq__(other)

    def __repr__ (self):

        key_str = ""
        if self.key == None:
            key_str = "No Key"
        else:
            key_str =  str(self.key)

        links_str = ""
        if len(self.links) == 0:
            links_str = "No Links"
        else:
            for link in self.links:
                links_str += "%s, " %self.links[link].key

        return key_str + "->{" + links_str + "}"

    def __str__ (self):

        return self.__repr__()





def __test__ ():
    class Obj:
        pass
    t = 't'
    f = 'f'
    o = Obj()
    seq1  = t,t
    seq2  = t,f
    seq2b = t,f,f
    seq2c = t
    seq3  = f,o

    def printer (args):
        print ('Fu: ', end='')
        for arg in args:
            print ('%s' %arg, end='')
        print ()
    def tf (args):
        print ('T F')
    def tff (args):
        print ('T F F')
    def t (args):
        print ('T')
    def fo (args):
        print ('F O')

    chain = KeyChain()
    chain.verbose = True
    chain.setup()
    chain.register_chain(seq1, printer, ('tt'))
    chain.register_chain(seq2, printer, ('tf'))
    chain.register_chain(seq2b, printer, ('tff'))
    chain.register_chain(seq2c, printer, ('t'))
    chain.register_chain(seq3, printer, ('fo'))

    try:
        while True:
            for char in raw_input():
                if char == 'o': char = o
                chain.handle(char)
    except EOFError:
        pass
    #input = t,t,f,f,t,t,t,t
    #for i in input:
    #    chain.handle(i)
    
    print('')

    return chain

if __name__ == "__main__":
    chain = __test__()

