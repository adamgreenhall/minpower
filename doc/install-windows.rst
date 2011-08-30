Windows Installation
====================================


Python installation 
--------------------

If you already use Python, see the required package list in :doc:`install-python-packages`.

If you are starting from scratch with Python, we are going to need Python and several :abbr:`packages (Think add-ons. In Python terms minpower is a package.)`.

* install `ActivePython <http://activestate.com/activepython/downloads>`_
* open a command prompt and install the **minpower**-required :doc:`install-python-packages` by typing::
    
        pypm install minpower pulp coopr numpy matplotlib networkx


Solver installation 
-----------------------------

Not sure which to pick? See :doc:`solvers`.

    * `GLPK <http://gnuwin32.sourceforge.net/packages/glpk.htm>`_         
    * `Gurobi <http://gurobi.com/doc/45/quickstart>`_
    * `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_ (tutorial coming soon)


.. _solver-to-python-windows:

Solver-to-Python hooks
-----------------------------

    Python needs to know where to find your solver. So we need to add the solver executable's folder to the path environment variable. 
    The following is an example of how to do this for a default GLPK install on a Windows 7 system:

    * open Control Panel, System and Security, System, and click `Advanced System Settings <_static/controlpanel.png>`_
    * open the Advanced tab, and click `Environment Variables <_static/systemproperties.png>`_
    * `select Path <_static/environmentvars.png>`_ in the User Variables list and click **Edit**
    * add ``;C:\Program Files (x86)\GnuWin32\bin`` to the end of the `Variable value <_static/editpath_glpk.png>`_.


**You are done!** Check out the resources :doc:`students` or :doc:`researchers` and try solving a problem.

Having trouble?
------------------
Check out :doc:`install-testing`.
