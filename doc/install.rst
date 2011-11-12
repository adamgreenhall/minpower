Installation
============

Basic full installation:

#. `ActivePython 2.7 <http://activestate.com/activepython/downloads>`_
#. ``pypm install minpower``
#. `GLPK <http://www.gnu.org/s/glpk>`_ (`Win <http://gnuwin32.sourceforge.net/packages/glpk.htm>`_, `Mac <http://www.arnab-deka.com/posts/2010/02/installing-glpk-on-a-mac/>`_)


1. Get Python
--------------
For new-to-Python folks, install `ActivePython 2.7 <http://activestate.com/activepython/downloads>`_. It makes the installation of a bunch of scientific :abbr:`packages (add-ons in Python terms)` very easy - the way it should be. 

For experienced Python users, ``pip install minpower`` should work just fine. If that command doesn't work, it is probably a failure to build scipy/numpy from source - try downloading the pre-built binary for your system from `SciPy <http://www.scipy.org/Download>_.

2. Get Minpower
-----------------

Simply run::
    
    pypm install minpower

3. Get a Solver
----------------

Minpower has been tested with `GLPK <http://www.gnu.org/s/glpk>`_, `Gurboi <http://gurobi.com>`_, and `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_.

But you can almost certainly use your favorite - here's `the full list <https://software.sandia.gov/trac/coopr/wiki/GettingStarted/Solvers>`_.

Not sure which to try? Here's a quick rundown on :doc:`solvers<solvers>`.

Test it out
------------

Go ahead and try to solve one of the test cases first, like::

    minpower uc

If you get an error about the problem not being solved - Python doesn't know where your solver is. To fix this here's a :doc:`guide to solver-to-Python connection<solver-connection>`. 
