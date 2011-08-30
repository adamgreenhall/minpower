Mac Installation
==========================


Add packages
-------------

If you already use Python, see the required package list in :doc:`install-python-packages`.

If you are starting from scratch with Python, we are going to need Python and several :abbr:`packages (Think add-ons. In Python terms minpower is a package.)`.

* install `ActivePython <http://activestate.com/activepython/downloads>`_
* open a command prompt and install the **minpower**-required :doc:`install-python-packages` by typing::
    
        pypm install minpower pulp coopr numpy matplotlib networkx

Add solvers
-------------

    * `GLPK <http://www.arnab-deka.com/posts/2010/02/installing-glpk-on-a-mac/>`_
    * `Gurobi <http://gurobi.com/doc/45/quickstart>`_
    * `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_ (tutorial coming soon)


.. _solver-to-python-mac:

solver-to-Python hooks
-----------------------

Gurobi
^^^^^^^

If you are using Gurobi, you may need to alter the PuLP configuration (in ``/Library/Frameworks/Python.framework/Versions/2.7/dist-packages/PuLP-1.4.8-py2.7.egg/pulp.cfg.linux``)
and change the gurobi path line to the location of your gurobi executable. E.g.:
    
    GurobiPath = /usr/local/gurobi/gurobi401/linux64/lib/python2.5

CPLEX 
^^^^^^

If you are using CPLEX, Python needs to know where to find it. So we need to modify the path environment variables.
The following is an example what needs to be added to the end of the ``~/.bashrc`` file using Ubunutu::

    export PATH="$PATH:/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/bin/x86-64_sles10_4.1"
    alias cplex='/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/bin/x86-64_sles10_4.1/cplex'
    export PYTHONPATH=$PYTHONPATH:/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/python/x86-64_sles10_4.1

..  note:: Your CPLEX root directory (in the case above ``/usr/ilog/CPLEX_Studio_AcademicResearch122/cplex/``) will probably be different.



**You are done!** Check out the resources :doc:`students` or :doc:`researchers` and try solving a problem.

Having trouble?
------------------
Check out :doc:`install-testing`.
