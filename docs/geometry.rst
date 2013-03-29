*****************************************
:mod:`geometry` --- 2D shapes and vectors
*****************************************

.. automodule:: geometry
    :no-members:

Vector Objects
==============
.. autoclass:: Vector

Shape Interface
===============
.. autoclass:: Shape
    :no-members:

    .. method:: get_top()
                get_left()
                get_bottom()
                get_right()

    Specify the outer dimensions, or the bounding rectangle, of the custom 
    shape.  These function must be redefined in subclasses.

    .. attribute:: top
                   left
                   bottom
                   right

    Provide convenient access to the shape properties.  These attributes are 
    automatically defined from the corresponding getter methods, so they should 
    not be reimplemented in subclasses.  Using these attributes should 
    generally be preferred over directly invoking the getter methods.

Rectangle Objects
=================
.. autoclass:: Rectangle

Miscellaneous Functions and Data
================================
Right now the geometry module contains a handful of miscellaneous mathematical 
helper functions and data.  In particular, it contains an assorted set of 
collision functions.  This will probably turn into a more comprehensive 
collision detection library in the future.  Until then, these functions will 
remain hacked onto the end of the geometry module.

.. data:: infinity

    Defined as float(inf)

.. data:: golden_ratio

    Defined as 1/2 + math.sqrt(5) / 2

.. autofunction:: circle_touching_line
.. autofunction:: clamp
