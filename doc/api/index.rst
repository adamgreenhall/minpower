Documentation
===============

This is an API for **Minpower**. Note the ``[source]`` link next to each code block - this provides a quick way to flip between source code and documentation. Use the tree and search box on the sidebar liberally. 

For basic use of the Minpower script, see :doc:`basic-use`. For a guide to creating problems using spreadsheets see :doc:`creating-problems`. 


:doc:`solving`
---------------------------------------

The :mod:`solve` module contains the top-level commands for reading data, creating problems, solving them, and saving results. Included is a function for solving rolling (or multi-stage) unit commitments, :func:`solve_multistage`.


:doc:`getting-data`
---------------------------------------

The module :mod:`get_data` reads in data from spreadsheet files and parse it into :class:`~powersystems.Generator`, :class:`~powersystems.Load`, :class:`~powersystems.Bus`, and :class:`~powersystems.Line` objects. The module also extracts the time information and create a :class:`~schedule.Timelist` object.


:doc:`power-systems`
---------------------------------------

The module :mod:`powersystems` models for power systems components, including :class:`~powersystems.PowerSystem`, :class:`~powersystems.Bus`, :class:`~powersystems.Generator`, :class:`~powersystems.Load`, and  :class:`~powersystems.Line`. Each of these objects inherits an optimization framework from :class:`~optimization.OptimizationObject`.

:doc:`time`
----------------------
The :mod:`schedule` module has models for times and schedule.


:doc:`optimization`
------------------------

:doc:`bids`
---------------------

:doc:`results`
--------------------

:doc:`testing`
--------------------

:doc:`add-ons`
---------------------


