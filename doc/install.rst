Installation
============

Honestly, installation can be a pain - *Windows and CPLEX are the toughest* - but it is worth it. 
The initial time investment will pay off quickly. 

If you are already a Python user or an optimization person you have probably
done some of these steps before. :doc:`Basic install on Linux <install-linux>` should take under 5min.

If you are new to this, you can follow the :doc:`install-tutorial`.


.. toctree::
    :hidden:
    
    install-linux
    install-tutorial

Prerequisites
--------------

#. `get Python <http://www.python.org/download/>`_

#. Install minpower's Python :ref:`dependency packages <packages-python>`: 
    
    pulp coopr numpy matplotlib networkx dateutil

#. Get an optimization solver (`Gurobi <http://gurobi.com>`_, `GLPK <http://www.gnu.org/software/glpk/>`_, or `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_). Not sure which to pick? See :doc:`solvers`.

    If your are using `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_ get the :ref:`solver-to-Python <solver-to-python>` hooks working (this can be frustrating).

.. toctree::
    :hidden:
    
    solvers


Get minpower
-------------

Install the `minpower package <http://pypi.python.org/pypi/minpower>`_ as you 
would :ref:`any Python package <packages-python>`. Or you can get 
the :ref:`most recent source <development>`.



Test it out
-------------

Using `Gurobi <http://gurobi.com>`_ or `GLPK <http://www.gnu.org/software/glpk/>`_? You are done! Check out the resources :doc:`students` or :doc:`researchers`.

If your are using `CPLEX <http://www.ibm.com/software/integration/optimization/cplex-optimizer>`_, we need to test that all the solver-to-Python hooks are working correctly. This can be a sticking point. Run the following script to make sure everything is working::
    
    from minpower.tests import solvers
    solvers.testall()

Do you see ``solved problem, status: Optimal`` after each of the solvers you installed? 

Great! Check out the resources :doc:`students` or :doc:`researchers`.

Do you see ``failed`` for a solver you did install? Well damn, it's not working yet. 
:ref:`Let's try troubleshooting <install-testing>`. 
