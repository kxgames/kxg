from pygame.locals import *

#######################################################################
#
#   Some event type constants overlap with key constants in pygame.
#   The purpose of making these mappings to provide unique identifiers
#   for each contsant.
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
    K_BACKSPACE : "K_BACKSPACE",        #   \b      backspace
    K_TAB : "K_TAB",                    #   \t      tab
    K_CLEAR : "K_CLEAR",                #           clear
    K_RETURN : "K_RETURN",              #   \r      return
    K_PAUSE : "K_PAUSE",                #   pause
    K_ESCAPE : "K_ESCAPE",              #   ^[      escape
    K_SPACE : "K_SPACE",                #   space
    K_EXCLAIM : "K_EXCLAIM",            #   !       exclaim
    K_QUOTEDBL : "K_QUOTEDBL",          #   "       quotedbl
    K_HASH : "K_HASH",                  #   #       hash
    K_DOLLAR : "K_DOLLAR",              #   $       dollar
    K_AMPERSAND : "K_AMPERSAND",        #   &       ampersand
    K_QUOTE : "K_QUOTE",                #   '       quote
    K_LEFTPAREN : "K_LEFTPAREN",        #   (       left parenthesis
    K_RIGHTPAREN : "K_RIGHTPAREN",      #   )       right parenthesis
    K_ASTERISK : "K_ASTERISK",          #   *       asterisk
    K_PLUS : "K_PLUS",                  #   +       plus sign
    K_COMMA : "K_COMMA",                #   ,       comma
    K_MINUS : "K_MINUS",                #   -       minus sign
    K_PERIOD : "K_PERIOD",              #   .       period
    K_SLASH : "K_SLASH",                #   /       forward slash
    K_0 : "K_0",                        #   0       0
    K_1 : "K_1",                        #   1       1
    K_2 : "K_2",                        #   2       2
    K_3 : "K_3",                        #   3       3
    K_4 : "K_4",                        #   4       4
    K_5 : "K_5",                        #   5       5
    K_6 : "K_6",                        #   6       6
    K_7 : "K_7",                        #   7       7
    K_8 : "K_8",                        #   8       8
    K_9 : "K_9",                        #   9       9
    K_COLON : "K_COLON",                #   :       colon
    K_SEMICOLON : "K_SEMICOLON",        #   ;       semicolon
    K_LESS : "K_LESS",                  #   <       less-than sign
    K_EQUALS : "K_EQUALS",              #   =       equals sign
    K_GREATER : "K_GREATER",            #   >       greater-than sign
    K_QUESTION : "K_QUESTION",          #   ?       question mark
    K_AT : "K_AT",                      #   @       at
    K_LEFTBRACKET : "K_LEFTBRACKET",    #   [       left bracket
    K_BACKSLASH : "K_BACKSLASH",        #   \       backslash
    K_RIGHTBRACKET : "K_RIGHTBRACKET",  #   ]      right bracket
    K_CARET : "K_CARET",                #   ^       caret
    K_UNDERSCORE : "K_UNDERSCORE",      #   _       underscore
    K_BACKQUOTE : "K_BACKQUOTE",        #           grave
    K_a : "K_a",                        #   a       a
    K_b : "K_b",                        #   b       b
    K_c : "K_c",                        #   c       c
    K_d : "K_d",                        #   d       d
    K_e : "K_e",                        #   e       e
    K_f : "K_f",                        #   f       f
    K_g : "K_g",                        #   g       g
    K_h : "K_h",                        #   h       h
    K_i : "K_i",                        #   i       i
    K_j : "K_j",                        #   j       j
    K_k : "K_k",                        #   k       k
    K_l : "K_l",                        #   l       l
    K_m : "K_m",                        #   m       m
    K_n : "K_n",                        #   n       n
    K_o : "K_o",                        #   o       o
    K_p : "K_p",                        #   p       p
    K_q : "K_q",                        #   q       q
    K_r : "K_r",                        #   r       r
    K_s : "K_s",                        #   s       s
    K_t : "K_t",                        #   t       t
    K_u : "K_u",                        #   u       u
    K_v : "K_v",                        #   v       v
    K_w : "K_w",                        #   w       w
    K_x : "K_x",                        #   x       x
    K_y : "K_y",                        #   y       y
    K_z : "K_z",                        #   z       z
    K_DELETE : "K_DELETE",              #           delete
    K_KP0 : "K_KP0",                    #           keypad 0
    K_KP1 : "K_KP1",                    #           keypad 1
    K_KP2 : "K_KP2",                    #           keypad 2
    K_KP3 : "K_KP3",                    #           keypad 3
    K_KP4 : "K_KP4",                    #           keypad 4
    K_KP5 : "K_KP5",                    #           keypad 5
    K_KP6 : "K_KP6",                    #           keypad 6
    K_KP7 : "K_KP7",                    #           keypad 7
    K_KP8 : "K_KP8",                    #           keypad 8
    K_KP9 : "K_KP9",                    #           keypad 9
    K_KP_PERIOD : "K_KP_PERIOD",        #   .       keypad period
    K_KP_DIVIDE : "K_KP_DIVIDE",        #   /       keypad divide
    K_KP_MULTIPLY : "K_KP_MULTIPLY",    #   *       keypad multiply
    K_KP_MINUS : "K_KP_MINUS",          #   -       keypad minus
    K_KP_PLUS : "K_KP_PLUS",            #   +       keypad plus
    K_KP_ENTER : "K_KP_ENTER",          #   \r      keypad enter
    K_KP_EQUALS : "K_KP_EQUALS",        #   =       keypad equals
    K_UP : "K_UP",                      #           up arrow
    K_DOWN : "K_DOWN",                  #           down arrow
    K_RIGHT : "K_RIGHT",                #           right arrow
    K_LEFT : "K_LEFT",                  #           left arrow
    K_INSERT : "K_INSERT",              #           insert
    K_HOME : "K_HOME",                  #           home
    K_END : "K_END",                    #           end
    K_PAGEUP : "K_PAGEUP",              #           page up
    K_PAGEDOWN : "K_PAGEDOWN",          #           page down
    K_F1 : "K_F1",                      #           F1
    K_F2 : "K_F2",                      #           F2
    K_F3 : "K_F3",                      #           F3
    K_F4 : "K_F4",                      #           F4
    K_F5 : "K_F5",                      #           F5
    K_F6 : "K_F6",                      #           F6
    K_F7 : "K_F7",                      #           F7
    K_F8 : "K_F8",                      #           F8
    K_F9 : "K_F9",                      #           F9
    K_F10 : "K_F10",                    #           F10
    K_F11 : "K_F11",                    #           F11
    K_F12 : "K_F12",                    #           F12
    K_F13 : "K_F13",                    #           F13
    K_F14 : "K_F14",                    #           F14
    K_F15 : "K_F15",                    #           F15
    K_NUMLOCK : "K_NUMLOCK",            #           numlock
    K_CAPSLOCK : "K_CAPSLOCK",          #           capslock
    K_SCROLLOCK : "K_SCROLLOCK",        #           scrollock
    K_RSHIFT : "K_RSHIFT",              #           right shift
    K_LSHIFT : "K_LSHIFT",              #           left shift
    K_RCTRL : "K_RCTRL",                #           right ctrl
    K_LCTRL : "K_LCTRL",                #           left ctrl
    K_RALT : "K_RALT",                  #           right alt
    K_LALT : "K_LALT",                  #           left alt
    K_RMETA : "K_RMETA",                #           right meta
    K_LMETA : "K_LMETA",                #           left meta
    K_LSUPER : "K_LSUPER",              #           left windows key
    K_RSUPER : "K_RSUPER",              #           right windows key
    K_MODE : "K_MODE",                  #           mode shift
    K_HELP : "K_HELP",                  #           help
    K_PRINT : "K_PRINT",                #           print screen
    K_SYSREQ : "K_SYSREQ",              #           sysrq
    K_BREAK : "K_BREAK",                #           break
    K_MENU : "K_MENU",                  #           menu
    K_POWER : "K_POWER",                #           power
    K_EURO : "K_EURO"                   #           euro
    }
    
string_to_key = {}
for key in key_to_string:
    string = key_to_string[key]
    string_to_key[string] = key

#######################################################################

type_to_string = {                          ##  event variables  ##
    QUIT : "QUIT",	     	            #   none
    ACTIVEEVENT : "ACTIVEEVENT",	    #   gain, state
    KEYDOWN : "KEYDOWN",	     	    #   unicode, key, mod
    KEYUP : "KEYUP",	     	            #   key, mod
    MOUSEMOTION : "MOUSEMOTION",	    #   pos, rel, buttons
    MOUSEBUTTONUP : "MOUSEBUTTONUP",        #   pos, button
    MOUSEBUTTONDOWN : "MOUSEBUTTONDOWN",    #   pos, button
    JOYAXISMOTION : "JOYAXISMOTION",        #   joy, axis, value
    JOYBALLMOTION : "JOYBALLMOTION",        #   joy, ball, rel
    JOYHATMOTION : "JOYHATMOTION",          #   joy, hat, value
    JOYBUTTONUP : "JOYBUTTONUP",            #   joy, button
    JOYBUTTONDOWN : "JOYBUTTONDOWN",        #   joy, button
    VIDEORESIZE : "VIDEORESIZE",            #   size, w, h
    VIDEOEXPOSE : "VIDEOEXPOSE",            #   none
    USEREVENT : "USEREVENT"                 #   code
    }

string_to_type = {}
for type in type_to_string:
    string = type_to_string[type]
    string_to_type[string] = type

#######################################################################

mouse_to_string = {
    1 : "LEFTBUTTON",
    2 : "MIDDLEBUTTON",
    3 : "RIGHTBUTTON",
    4 : "ROLLUP",
    5 : "ROLLDOWN",
    6 : "LEFTEXTRABUTTON",
    7 : "RIGHTEXTRABUTTON"
    }

string_to_mouse = {}
for mouse in mouse_to_string:
    string = mouse_to_string[mouse]
    string_to_mouse[string] = mouse
