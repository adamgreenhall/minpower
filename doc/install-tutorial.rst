Step-by-Step Installation
==========================

Currently these instructions are written for Linux (tested on an Ubuntu machine). 
They should be similar for Macs. A Windows tutorial will be coming soon.


.. _packages-python:

Python Packages
^^^^^^^^^^^^^^^

Python packages are open source add-ons that provide great functionality not included in the Python core. 
They can be installed on Mac/Linux systems by using `pip <http://pypi.python.org/pypi/pip>`_. For example::

    sudo pip install matplotlib

You can get all the **minpower**-required packages by running::

    sudo pip install pulp coopr numpy matplotlib networkx dateutil

or by downloading each one from the Python `package index <http://pypi.python.org/pypi>`_ and installing by running::
    
    cd download_directory
    python setup.py install


================     ===================================
Package              Use in minpower
================     ===================================
pulp                 optimization (current)
coopr                optimization (future)
numpy                matrix and polynomial math
matplotlib           visualization
networkx             visualization of graphs (for OPF)
dateutil             parses dates and times
================     ===================================

.. note:: If you are using Mac OSX and are having trouble with installing ``matplotlib`` through ``pip`` - this is a common issue. Check out the `matplotlib installation instructions <http://matplotlib.sourceforge.net/users/installing.html>`_ for your options, including letting the `Enthought Python Distribution <http://www.enthought.com>`_ do it all for you.

.. _solver-to-python:

Solver installation 
^^^^^^^^^^^^^^^^^^^
Not sure which to pick? See :doc:`solvers`.

    * `GLPK <http://www.gnu.org/software/glpk/>`_ is packaged for most linux distros. Just run::
    
        sudo apt-get install glpk
        
    * `Gurobi <http://gurobi.com>`_ has `good instructions on their website <http://gurobi.com/doc/45/quickstart/>`_
    * `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_ is complicated (tutorial comming soon)

CPLEX solver-to-Python hooks
-----------------------------

    Good news if you are using GLPK or Gurobi - you are done. If you are using CPLEX, Python needs to know where to find it. 
    So we need to modify the path environment variables. The following is an example what needs to be added to the end of
    the ``~/.bashrc`` file using Ubunutu::

        export PATH="$PATH:/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/bin/x86-64_sles10_4.1"
        alias cplex='/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/bin/x86-64_sles10_4.1/cplex'
        export PYTHONPATH=$PYTHONPATH:/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/python/x86-64_sles10_4.1

    ..  note:: Different Linux systems may have a different name for the ``.bashrc`` file. Your CPLEX root directory (in the case above ``/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/``) will probably be different.

.. comment: may need to add in hooks for Gurobi by modifying 
    
    /usr/local/lib/python2.7/dist-packages/PuLP-1.4.8-py2.7.egg/pulp.cfg.linux
    change the gurobi path line to:    
    GurobiPath = /usr/local/gurobi/gurobi401/linux64/lib/python2.5



Getting minpower
^^^^^^^^^^^^^^^^^^^^^^^

Install **minpower** as you would :ref:`any Python package <packages-python>`. (Or you can get
the :ref:`most recent source <development>`). 


The easy way::

    sudo pip install minpower


.. _install-testing:

Installation Testing
^^^^^^^^^^^^^^^^^^^^^^^

Using `Gurobi <http://gurobi.com>`_ or `GLPK <http://www.gnu.org/software/glpk/>`_? You are done! Check out the resources :doc:`students` or :doc:`researchers`.


If your are using `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_, we need to test that all the solver-to-Python hooks are working correctly. This can be a sticking point. Run the following script to make sure everything is working::
    
    from minpower.tests import solvers
    solvers.testall()

which executes the code below:

.. literalinclude:: ../minpower/tests/solvers.py


Do you see ``solved problem, status: Optimal`` after each of the solvers you installed? 

Great! Check out the resources :doc:`students` or :doc:`researchers`.

Do you see ``failed`` for a solver you did install? Well damn, it's not working yet. 

Try:

    #. check that you set your :ref:`solver-to-Python <solver-to-python>` hooks
    #. call the solvers from the command line. GLPK is ``glpsol``. Gurobi is ``gurobi``. 
       With the :ref:`alias <solver-to-python>` CPLEX should be ``cplex``. If this doesn't work
       perhaps re-install your solver.
    #. if you are still having trouble, consider trying a different solver first
