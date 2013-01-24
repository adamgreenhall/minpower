Configuration
=============

Minpower's behavior is mostly configured by setting flags at runtime. For instance::
    
    minpower unit_commitment_problem/ --solver cplex --breakpoints 5 --hours_overlap 12 --reserve_load_fraction 0.10
    
solves the problem with the CPLEX solver, using 5 breakpoint bid curves, 12hrs of overlap between the commitments, and requires reserves equal to 10% of the load.


If you find yourself always overriding certain defaults (like the default solver), you can also put configuration options in a .minpowerrc or minpower.cfg file in your home directory. These are standard .ini-style config files. The default is `here  <https://github.com/adamgreenhall/minpower/blob/master/minpower/configuration/minpower.cfg>`_.