Documentation
===============

This is an API for **Minpower**. Note the ``[source]`` link next to each code block - this provides a quick way to flip between source code and documentation. Use the tree and search box on the sidebar liberally. 

For basic use of the Minpower script, see :doc:`../basic-use`. For a guide to creating problems using spreadsheets see :doc:`../creating-problems`. 


:doc:`solving`
---------------------------------------

The :mod:`solve` module contains the top-level commands for reading data, creating problems, solving them, and saving results. Included is a function for solving rolling (or multi-stage) unit commitments, :func:`~solve.solve_multistage`.


:doc:`getting-data`
---------------------------------------

The module :mod:`get_data` reads in data from spreadsheet files and parse it into :class:`~powersystems.Generator`, :class:`~powersystems.Load`, :class:`~powersystems.Bus`, and :class:`~powersystems.Line` objects. The module also extracts the time information and create a :class:`~schedule.Timelist` object.


:doc:`power-systems`
---------------------------------------

The module :mod:`powersystems` models for power systems components, including :class:`~powersystems.PowerSystem`, :class:`~powersystems.Bus`, :class:`~powersystems.Generator`, :class:`~powersystems.Load`, and  :class:`~powersystems.Line`. Each of these objects inherits an optimization framework from :class:`~optimization.OptimizationObject`.

:doc:`time`
----------------------
The :mod:`schedule` module has models for times (:class:`~schedule.Timelist`) and schedules (:class:`~schedule.Schedule`).


:doc:`optimization`
------------------------
The :mod:`optimization` module has an optimization problem model (:class:`~optimization.Problem`) and a template for optimization objects (:class:`~optimization.OptimizationObject`).

:doc:`bids`
---------------------
The :mod:`bidding` module has models for the piece-wise linearization of polynomials and a container for these models (:class:`~bidding.Bid`).

:doc:`results`
--------------------
The :mod:`results` module has models for power systems problem solutions. These contain the code for visualization and output to spreadsheets. 

:doc:`testing`
--------------------
The :mod:`test` subpackage has both unit tests (of individual constraints) and a directory structure full of example cases (for integration testing).


:doc:`add-ons`
---------------------
The :mod:`addons` subpackage is the place to create and integrate your own modules.


.. toctree::
    :maxdepth: 1
    
    solving
    getting-data
    power-systems
    time
    optimization
    bids
    results
    testing
    add-ons
    


