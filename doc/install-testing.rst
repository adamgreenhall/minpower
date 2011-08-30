Installation Testing
=======================


Getting all the solver-to-Python hooks working correctly can be a sticking point. 
If you are having trouble with this (reports that PuLP can't find the solver), open 
a Python prompt and type::
    
    from minpower.tests import solvers
    solvers.testall()

Do you see ``solved problem, status: Optimal`` after each of the solvers you installed? 

Great! Check out the resources :doc:`students` or :doc:`researchers`.

Do you see ``failed`` for a solver you did install?

Try:

    #. Check that you set your solver-to-Python hooks correctly (for :ref:`Linux <solver-to-python-linux>`, :ref:`Mac <solver-to-python-mac>`, :ref:`Win <solver-to-python-windows>`)
    #. Call the solvers from the command line. After following the solver-to-Python directions above
       CPLEX should be called by ``cplex``, GLPK by ``glpsol``, Gurobi by ``gurobi``. 
       If this doesn't work check your Path variable and **reopen the command prompt**.
    #. If you are still having trouble, consider trying a different solver first.

