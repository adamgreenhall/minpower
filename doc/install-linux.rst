Linux Installation
==========================

These are the get-**minpower**-working-as-fast-as-possible install instructions for Linux, written for Ubuntu.


Run::
    
    sudo apt-get install python-pip python-numpy python-matplotlib glpk
    sudo pip install pulp coopr networkx minpower


Two commands and **you are up and running!** Check out the resources :doc:`students` or :doc:`researchers`.


Or continue on to add a research-grade solver.

Add solvers
-------------

    * `Gurobi <http://gurobi.com/doc/45/quickstart>`_
    * `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_ (tutorial coming soon)


.. _solver-to-python-linux:

solver-to-Python hooks
-----------------------



Gurobi
^^^^^^^

If you are using Gurobi, the PuLP configuration may need to be modified::

    sudo gedit /usr/local/lib/python2.7/dist-packages/PuLP-1.4.8-py2.7.egg/pulp/pulp.cfg.linux
    
and change the gurobi path line to:    
    
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
