*****************
How to Contribute
*****************
You can contribute to the kxg game engine either by reporting bugs, writing
documentation, writing demo games or example snippets, or developing code for 
the engine itself.  Report bugs using the `issue tracker on GitHub 
<https://github.com/kxgames/kxg/issues>`_.  Contribute documentation or code by 
forking the `main repository on GitHub <https://github.com/kxgames/kxg>`_ and 
making a pull request.

Conventions
===========
For developing code, follow the style guidelines laid out in `PEP8 
<https://www.python.org/dev/peps/pep-0008/>`_.  For documenting arguments and 
return values in docstrings, follow the `NumPy convention 
<https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`_.

Running the tests
=================
If you want to develop code, you'll want to know how to work with the tests.  
Loosely speaking, the game engine has two kinds of tests.  The first are the 
unit tests and the second is an executable for a do-nothing game.  The unit 
tests are very rigorous and should at the very least cover every line of code 
in the engine.  The dummy game is more of a debugging tool; it doesn't really 
test anything but it can be useful when you're writing code.

The unit tests are based on the `pytest framework 
<http://pytest.org/latest/>`_, so you have to install that before you run them:

.. code-block:: bash
    
    pip install pytest

To run the unit tests, move into the test directory and run the following 
command:

.. code-block:: bash
    
    ./run_tests.py

You can pass this script any option that you could pass to pytest.  The 
following options are implicitly specified:
    
* ``-x`` Stop on the first error.

* ``--color=yes`` Output the test report in color, even if the report is 
  being piped through ``less`` or something.

* ``--cov=kxg --cov-report=html`` Generate an HTML coverage report for the 
  ``kxg`` module.  This is a good way to see what parts of the code aren't 
  being tested.

By default, all of the tests matching the pattern ``??_test_*.py`` (where the 
?'s are numbers) will be run.  The numbers prefixing each test control the 
order in which the tests will be run.  You can also specify one or more tests 
on the command-line, in which case only those tests will be run.

Writing new tests
=================
Tests are written using the `pytest framework <http://pytest.org/latest/>`_, so 
making a new test is as simple as writing a new function whose name starts with 
``test_``.  The tests are run in the order they're written, so try to put your 
test somewhere where everything you're assuming will work has already been 
tested.
