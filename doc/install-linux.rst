Linux Installation
==========================

These are the get-**minpower**-working-as-fast-as-possible install instructions for Linux, written for Ubuntu.


Run::
    
    sudo apt-get install python-pip python-numpy python-matplotlib glpk
    sudo pip install pulp coopr networkx minpower



.. comment
    and see if it is working (in a Python shell)::
        
        import minpower
        minpower.tests.solvers.testall()

    For a working installation, GLPK should solve the test problem and return ``Optimal`` 
    (don't worry if CPLEX and Gurobi fail, you don't have them installed). If not, 
    here is the :ref:`troubleshooting <install-testing>`.
