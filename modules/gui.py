from __future__ import print_function

import copy
from pygame.locals import *

# Things to do:
#   ~ Add a universal reset key (ie. ESC). Or other universal trigger
#       keys. 
#       NOTE: a reset key is pointless... Just never register the
#       key and it will always fail, thereby resetting the chain.
#   ~ Add ability to handle modifier keys such as Shift or Ctrl.
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

class Keychain:

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

        new_lens = Lens (self, name, copy.copy(lens))
        self.lenses[name] = new_lens

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

    def handle (self, input, lens_only=False):
        # Print out some messages
        if self.verbose and lens_only == False:
            print ('Checking input %s' %input)
            if len(self.sequence) > 0:
                print ('    Current_sequence: ', end='')
                for item in self.sequence[:-1]:
                    print ('%s, ' %item, end='')
                else:
                    print ('%s' %self.sequence[-1])

        # See if the input is really a lens.
        if input in self.lenses:
            lens = self.lenses[input]

            # Toggle the lens.
            if lens in self.active_lenses:
                if self.verbose:
                    print ('Deactivating the %s lens' %lens.get_name())
                self.active_lenses.remove (lens)

            else:
                if self.verbose:
                    print ('Activating the %s lens' %lens.get_name())
                self.active_lenses.append (lens)

        elif not lens_only:
            # For any active lenses, create the image of the input
            # through the lens.
            for lens in self.active_lenses:
                if input in lens:
                    if self.verbose:
                        print ('Applying the %s lens' %lens.get_name())
                        print ('    %s  ->  %s' %(input, lens[input]))
                    input = lens[input]

            # Give the input to the active node.
            self.sequence.append(input)
            self.active.check(input)
    
    def activate (self, new):
        self.active = new

    def reset (self):
        self.sequence = []
        self.activate (self.root_node)


class Lens (dict):

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

    def __str__ (self):
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
        #if self.verbose: print (input, end='')

        # If the current Node has a link that matches the input, execute
        # that link's callbacks. Otherwise, the sequence breaks.

        if input in self.links:
            if self.verbose: print ('    %s OK.' %input)
            self.links[input].execute()

        else:
            if self.verbose: print ('    %s fails.' %input)
            self.break_sequence()
    
    def execute (self):
        if self.verbose:
            if len(self.callbacks) > 0:
                seq = self.manager.sequence
                for member in seq[:-1]:
                    print ('%s, ' %member, end='')
                else:
                    print ('%s passes. ' %seq[-1])
                    print ('    Now calling:')
                    
        if len(self.links) > 0: self.select()
        else: self.manager.reset()

        for callback in self.callbacks:
            if self.verbose:
                print('      %s' %callback[0])
            args = callback[1]
            callback[0](args)

    def select (self):
        self.manager.activate(self)

    def break_sequence (self):
        self.manager.reset()



#######################################################################
#
#   Some event type constants overlap with key constants in pygame.
#   The purpose of making these mappings to provide unique identifiers
#   for each constant.
# 
#   For more info on pygame events see:
#       http://www.pygame.org/docs/ref/key.html
#       http://www.pygame.org/docs/ref/event.html
#
#######################################################################
# Contains:              Mapping example
#
#   key_to_string        K_A  --> "K_A"
#   string_to_key       "K_A" -->  K_A
#
#   type_to_string       KEYUP  --> "KEYUP"
#   string_to_type      "KEYUP" -->  KEYUP
#
#######################################################################

key_to_string = {
    K_BACKSPACE : 'K_BACKSPACE',        #   \b      backspace
    K_TAB : 'K_TAB',                    #   \t      tab
    K_CLEAR : 'K_CLEAR',                #           clear
    K_RETURN : 'K_RETURN',              #   \r      return
    K_PAUSE : 'K_PAUSE',                #   pause
    K_ESCAPE : 'K_ESCAPE',              #   ^[      escape
    K_SPACE : 'K_SPACE',                #   space
    K_EXCLAIM : 'K_EXCLAIM',            #   !       exclaim
    K_QUOTEDBL : 'K_QUOTEDBL',          #   '       quotedbl
    K_HASH : 'K_HASH',                  #   #       hash
    K_DOLLAR : 'K_DOLLAR',              #   $       dollar
    K_AMPERSAND : 'K_AMPERSAND',        #   &       ampersand
    K_QUOTE : 'K_QUOTE',                #   '       quote
    K_LEFTPAREN : 'K_LEFTPAREN',        #   (       left parenthesis
    K_RIGHTPAREN : 'K_RIGHTPAREN',      #   )       right parenthesis
    K_ASTERISK : 'K_ASTERISK',          #   *       asterisk
    K_PLUS : 'K_PLUS',                  #   +       plus sign
    K_COMMA : 'K_COMMA',                #   ,       comma
    K_MINUS : 'K_MINUS',                #   -       minus sign
    K_PERIOD : 'K_PERIOD',              #   .       period
    K_SLASH : 'K_SLASH',                #   /       forward slash
    K_0 : 'K_0',                        #   0       0
    K_1 : 'K_1',                        #   1       1
    K_2 : 'K_2',                        #   2       2
    K_3 : 'K_3',                        #   3       3
    K_4 : 'K_4',                        #   4       4
    K_5 : 'K_5',                        #   5       5
    K_6 : 'K_6',                        #   6       6
    K_7 : 'K_7',                        #   7       7
    K_8 : 'K_8',                        #   8       8
    K_9 : 'K_9',                        #   9       9
    K_COLON : 'K_COLON',                #   :       colon
    K_SEMICOLON : 'K_SEMICOLON',        #   ;       semicolon
    K_LESS : 'K_LESS',                  #   <       less-than sign
    K_EQUALS : 'K_EQUALS',              #   =       equals sign
    K_GREATER : 'K_GREATER',            #   >       greater-than sign
    K_QUESTION : 'K_QUESTION',          #   ?       question mark
    K_AT : 'K_AT',                      #   @       at
    K_LEFTBRACKET : 'K_LEFTBRACKET',    #   [       left bracket
    K_BACKSLASH : 'K_BACKSLASH',        #   \       backslash
    K_RIGHTBRACKET : 'K_RIGHTBRACKET',  #   ]      right bracket
    K_CARET : 'K_CARET',                #   ^       caret
    K_UNDERSCORE : 'K_UNDERSCORE',      #   _       underscore
    K_BACKQUOTE : 'K_BACKQUOTE',        #           grave
    K_a : 'K_a',                        #   a       a
    K_b : 'K_b',                        #   b       b
    K_c : 'K_c',                        #   c       c
    K_d : 'K_d',                        #   d       d
    K_e : 'K_e',                        #   e       e
    K_f : 'K_f',                        #   f       f
    K_g : 'K_g',                        #   g       g
    K_h : 'K_h',                        #   h       h
    K_i : 'K_i',                        #   i       i
    K_j : 'K_j',                        #   j       j
    K_k : 'K_k',                        #   k       k
    K_l : 'K_l',                        #   l       l
    K_m : 'K_m',                        #   m       m
    K_n : 'K_n',                        #   n       n
    K_o : 'K_o',                        #   o       o
    K_p : 'K_p',                        #   p       p
    K_q : 'K_q',                        #   q       q
    K_r : 'K_r',                        #   r       r
    K_s : 'K_s',                        #   s       s
    K_t : 'K_t',                        #   t       t
    K_u : 'K_u',                        #   u       u
    K_v : 'K_v',                        #   v       v
    K_w : 'K_w',                        #   w       w
    K_x : 'K_x',                        #   x       x
    K_y : 'K_y',                        #   y       y
    K_z : 'K_z',                        #   z       z
    K_DELETE : 'K_DELETE',              #           delete
    K_KP0 : 'K_KP0',                    #           keypad 0
    K_KP1 : 'K_KP1',                    #           keypad 1
    K_KP2 : 'K_KP2',                    #           keypad 2
    K_KP3 : 'K_KP3',                    #           keypad 3
    K_KP4 : 'K_KP4',                    #           keypad 4
    K_KP5 : 'K_KP5',                    #           keypad 5
    K_KP6 : 'K_KP6',                    #           keypad 6
    K_KP7 : 'K_KP7',                    #           keypad 7
    K_KP8 : 'K_KP8',                    #           keypad 8
    K_KP9 : 'K_KP9',                    #           keypad 9
    K_KP_PERIOD : 'K_KP_PERIOD',        #   .       keypad period
    K_KP_DIVIDE : 'K_KP_DIVIDE',        #   /       keypad divide
    K_KP_MULTIPLY : 'K_KP_MULTIPLY',    #   *       keypad multiply
    K_KP_MINUS : 'K_KP_MINUS',          #   -       keypad minus
    K_KP_PLUS : 'K_KP_PLUS',            #   +       keypad plus
    K_KP_ENTER : 'K_KP_ENTER',          #   \r      keypad enter
    K_KP_EQUALS : 'K_KP_EQUALS',        #   =       keypad equals
    K_UP : 'K_UP',                      #           up arrow
    K_DOWN : 'K_DOWN',                  #           down arrow
    K_RIGHT : 'K_RIGHT',                #           right arrow
    K_LEFT : 'K_LEFT',                  #           left arrow
    K_INSERT : 'K_INSERT',              #           insert
    K_HOME : 'K_HOME',                  #           home
    K_END : 'K_END',                    #           end
    K_PAGEUP : 'K_PAGEUP',              #           page up
    K_PAGEDOWN : 'K_PAGEDOWN',          #           page down
    K_F1 : 'K_F1',                      #           F1
    K_F2 : 'K_F2',                      #           F2
    K_F3 : 'K_F3',                      #           F3
    K_F4 : 'K_F4',                      #           F4
    K_F5 : 'K_F5',                      #           F5
    K_F6 : 'K_F6',                      #           F6
    K_F7 : 'K_F7',                      #           F7
    K_F8 : 'K_F8',                      #           F8
    K_F9 : 'K_F9',                      #           F9
    K_F10 : 'K_F10',                    #           F10
    K_F11 : 'K_F11',                    #           F11
    K_F12 : 'K_F12',                    #           F12
    K_F13 : 'K_F13',                    #           F13
    K_F14 : 'K_F14',                    #           F14
    K_F15 : 'K_F15',                    #           F15
    K_NUMLOCK : 'K_NUMLOCK',            #           numlock
    K_CAPSLOCK : 'K_CAPSLOCK',          #           capslock
    K_SCROLLOCK : 'K_SCROLLOCK',        #           scrollock
    K_RSHIFT : 'K_RSHIFT',              #           right shift
    K_LSHIFT : 'K_LSHIFT',              #           left shift
    K_RCTRL : 'K_RCTRL',                #           right ctrl
    K_LCTRL : 'K_LCTRL',                #           left ctrl
    K_RALT : 'K_RALT',                  #           right alt
    K_LALT : 'K_LALT',                  #           left alt
    K_RMETA : 'K_RMETA',                #           right meta
    K_LMETA : 'K_LMETA',                #           left meta
    K_LSUPER : 'K_LSUPER',              #           left windows key
    K_RSUPER : 'K_RSUPER',              #           right windows key
    K_MODE : 'K_MODE',                  #           mode shift
    K_HELP : 'K_HELP',                  #           help
    K_PRINT : 'K_PRINT',                #           print screen
    K_SYSREQ : 'K_SYSREQ',              #           sysrq
    K_BREAK : 'K_BREAK',                #           break
    K_MENU : 'K_MENU',                  #           menu
    K_POWER : 'K_POWER',                #           power
    K_EURO : 'K_EURO'                   #           euro
    }
    
string_to_key = {}
for key in key_to_string:
    string = key_to_string[key]
    string_to_key[string] = key

#######################################################################

type_to_string = {                          ##  event variables  ##
    QUIT : 'QUIT',	     	            #   none
    ACTIVEEVENT : 'ACTIVEEVENT',	    #   gain, state
    KEYDOWN : 'KEYDOWN',	     	    #   unicode, key, mod
    KEYUP : 'KEYUP',	     	            #   key, mod
    MOUSEMOTION : 'MOUSEMOTION',	    #   pos, rel, buttons
    MOUSEBUTTONUP : 'MOUSEBUTTONUP',        #   pos, button
    MOUSEBUTTONDOWN : 'MOUSEBUTTONDOWN',    #   pos, button
    JOYAXISMOTION : 'JOYAXISMOTION',        #   joy, axis, value
    JOYBALLMOTION : 'JOYBALLMOTION',        #   joy, ball, rel
    JOYHATMOTION : 'JOYHATMOTION',          #   joy, hat, value
    JOYBUTTONUP : 'JOYBUTTONUP',            #   joy, button
    JOYBUTTONDOWN : 'JOYBUTTONDOWN',        #   joy, button
    VIDEORESIZE : 'VIDEORESIZE',            #   size, w, h
    VIDEOEXPOSE : 'VIDEOEXPOSE',            #   none
    USEREVENT : 'USEREVENT'                 #   code
    }

string_to_type = {}
for type in type_to_string:
    string = type_to_string[type]
    string_to_type[string] = type

#######################################################################

mouse_to_string = {
    1 : 'LEFTBUTTON',
    2 : 'MIDDLEBUTTON',
    3 : 'RIGHTBUTTON',
    4 : 'ROLLUP',
    5 : 'ROLLDOWN',
    6 : 'LEFTEXTRABUTTON',
    7 : 'RIGHTEXTRABUTTON'
    }

string_to_mouse = {}
for mouse in mouse_to_string:
    string = mouse_to_string[mouse]
    string_to_mouse[string] = mouse

def module_test():

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

    while True:
        try:
            for char in raw_input():
                if char == 'o': char = o
                chain.handle(char)
        except EOFError:
            break

    #input = t,t,f,f,t,t,t,t
    #for i in input:
    #    chain.handle(i)
    
    print('')
    return chain

if __name__ == '__main__':
    chain = module_test()

