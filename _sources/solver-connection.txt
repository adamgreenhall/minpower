Solver Connection
===================

Python has to know where to find your solver to be able to use it. Here are operating system dependent instructions for how to make that happen:

Mac
-----

* Use a text editor to open ``~/.bash_profile``
* Add your solver's ``\bin`` directory to the path, e.g.::
    
    export PATH=$PATH:/Library/gurobi452/mac64/bin/

Windows
---------

* open Control Panel, System and Security, System, and click `Advanced System Settings <_static/controlpanel.png>`_
* open the Advanced tab, and click `Environment Variables <_static/systemproperties.png>`_
* `select PATH <_static/environmentvars.png>`_ in the User Variables list and click **Edit**
* add your solver install directory to the end of the `Variable value <_static/editpath_glpk.png>`_, e.g. here is the GLPK path location on my machine::
    
    ;C:\Program Files (x86)\GnuWin32\bin


Linux
---------

* Use a text editor to open ``~/.bashrc``
* Add your solver's ``\bin`` directory to the path, e.g.::
    
    export PATH=$PATH:/opt/gurobi452/linux64/bin/

Testing
---------

    #. Check that you set your solver-to-Python connection correctly (by the instructions above)
    #. Call the solvers from the command line. After following the solver-to-Python directions above
       CPLEX should be called by ``cplex``, GLPK by ``glpsol``, Gurobi by ``gurobi``. 
       If this doesn't work check your Path variable and **reopen the command prompt**.
    #. If you are still having trouble, make sure your solver is installed correctly (and exactly where you think it should be), or consider trying a different solver first.