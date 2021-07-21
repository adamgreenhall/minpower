Basic Use
==========

The easiest way to use **Minpower** is by using the ``minpower`` script from the command line. Simply create a folder (e.g. ``mycommitment/``) containing spreadsheets to specify the power systems problem you are trying to solve. Spreadsheet creation is described in detail in :doc:`creating-problems`. 

To solve the problem call::
    
    minpower mycommitment

Your problem is created and sent to an optimization solver on your computer and the results (in spreadsheet and graphical forms) are saved to the folder. Basic use is as easy as that.

You can also specify a number of options from the command line. For example, to use the CPLEX solver::
    
    minpower mycommitment --solver cplex

A full list of options is available by calling::
    
    minpower --help

There are many examples of **Minpower** problems in the `test folders on github   <https://github.com/adamgreenhall/minpower/tree/master/minpower/tests>`_.