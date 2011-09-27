Why minpower?
==============

**minpower** is designed to make solving :doc:`ED <economic-dispatch>`, :doc:`OPF <optimal-power-flow>`, and :doc:`UC <unit-commitment>` problems easy and beautiful. 
Traditional approaches to solving these problems are limited by:
    
    *  :abbr:`low level (like C++ or GMPL)` languages
    *  :abbr:`expensive (CPLEX, GAMMS, AMPL, AIMMS, ...)` software
    *  being :abbr:`solver dependent (*only* CPLEX or *only* GLPK)`
    
Behold minpower!
^^^^^^^^^^^^^^^^^

    * written in `Python <http://www.python.org/about/>`_
    * :ref:`free <license>` and :ref:`open source <development>`
    * can use many :doc:`solvers <solvers>`
    * :abbr:`comparable solution times (For large problems optimization takes most of the solution time. minpower farms out its optimization to CPLEX with little overhead. Test results coming soon.)` 


Sounds great: :doc:`get it now <install>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
