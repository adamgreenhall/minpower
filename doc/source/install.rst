Installation
============

.. container:: basic-installation     

    Basic full installation:

    #. ``python3 -m pip install minpower``
    #. `GLPK <http://www.gnu.org/s/glpk>`_ (`Win <http://gnuwin32.sourceforge.net/packages/glpk.htm>`_, `Mac <http://www.arnab-deka.com/posts/2010/02/installing-glpk-on-a-mac/>`_)


1. Get Python
----------------

You'll need python3. Instructions for `Windows <https://docs.python-guide.org/starting/install3/win/>`_, `MacOS <https://docs.python-guide.org/starting/install3/osx/>`_, `Linux <https://docs.python-guide.org/starting/install3/linux/>`_ 

2. Get Minpower
----------------

``python3 -m pip install minpower``

3. Get a Solver
----------------

Minpower has been tested with `GLPK <http://www.gnu.org/s/glpk>`_, `CBC <https://projects.coin-or.org/Cbc>`_, `Gurboi <http://gurobi.com>`_, and `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_.

But you can almost certainly use your favorite - here's `the full list <https://pyomo.readthedocs.io/en/stable/solving_pyomo_models.html#supported-solvers>`_.

Not sure which to try? Here's a quick rundown on :doc:`solvers<solvers>`.

You will need to add the solver to your path. See :doc:`guide to solver-to-Python connection<solver-connection>`.

For a quick and easy solver installation on MacOS, run: ``brew install glpk``

Test it out
------------

Go ahead and download  `the basic unit commitment test case <https://github.com/downloads/adamgreenhall/minpower/uc.zip>`_ and try and solve it first, using the terminal::

    minpower uc

If you get an error about the problem not being solved - Python probably doesn't know where your solver is. To fix this here's a :doc:`guide to solver-to-Python connection<solver-connection>`. 


Stochastic UC
---------------

For stochastic problems you will need to install `PySP <https://github.com/Pyomo/pysp>`_ via ``pip install http://github.com/Pyomo/pysp/tarball/v6.0#egg=pysp-1.0``