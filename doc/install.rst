Installation
============

.. container:: basic-installation     

    Basic full installation:

    #. `ActivePython 2.7 <http://activestate.com/activepython/downloads>`_
    #. ``pypm install minpower``
    #. `GLPK <http://www.gnu.org/s/glpk>`_ (`Win <http://gnuwin32.sourceforge.net/packages/glpk.htm>`_, `Mac <http://www.arnab-deka.com/posts/2010/02/installing-glpk-on-a-mac/>`_)

1. Get Python
--------------
For new-to-Python folks, install `ActivePython 2.7 <http://activestate.com/activepython/downloads>`_. It makes the installation of a bunch of scientific :abbr:`packages (add-ons in Python terms)` very easy - the way it should be. Note that the 32-bit version is free for Windows, while for the 64-bit version only the Business Edition has a package manager. 

For Windows users, add:: 

  C:\Python27\;C:\Python27\Scripts\

to your PATH environment variable and create a new PYTHONPATH environment variable and add ``C:\Python27``.

For experienced Python users, ``pip install minpower`` should work just fine. If that command doesn't work, it is probably a failure to build scipy/numpy from source - try downloading the pre-built binary for your system from `SciPy <http://www.scipy.org/Download>`_.

2. Get Minpower
-----------------

Simply run::
    
    pip install minpower

3. Get a Solver
----------------

Minpower has been tested with `GLPK <http://www.gnu.org/s/glpk>`_, `Gurboi <http://gurobi.com>`_, and `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_.

But you can almost certainly use your favorite - here's `the full list <https://software.sandia.gov/trac/coopr/wiki/GettingStarted/Solvers>`_.

Not sure which to try? Here's a quick rundown on :doc:`solvers<solvers>`.

You will need to add the solver to your path. See :doc:`guide to solver-to-Python connection<solver-connection>`.

Test it out
------------

Go ahead and download `the basic unit commitment:<https://github.com/downloads/adamgreenhall/minpower/uc.zip test case>`_ and try and solve it first, like::

    minpower uc

If you get an error about the problem not being solved - Python probably doesn't know where your solver is. To fix this here's a :doc:`guide to solver-to-Python connection<solver-connection>`. 
