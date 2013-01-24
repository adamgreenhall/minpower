Creating a Problem
====================

Minpower solves problems that are defined in spreadsheets. The most basic :abbr:`ED (Economic Dispatch)` problem only has two files: ``generators.csv`` and ``loads.csv``. If you are solving an :abbr:`UC (Unit Commitment)` then you need to define the initial conditions for your generation in ``initial.csv``. Scheduled or predicted energy amounts (e.g. predicted wind farm output or predicted load demand) over a series of times can be specified in a file defined by the ``schedule file name`` column of the component. If you are solving an :abbr:`OPF (Optimal Power Flow)`, then you also need to define your transmission lines in ``lines.csv``.

The following tables give details on how to describe each component using spreadsheet columns. (Column order does not matter. Capitalization, underscores, and spaces are all ignored in the header row column names.) Examples spreadsheets are given after each table.

.. create these files by using pandoc (create-problem-tables.sh)

Generators
-----------

.. include:: creating-problems-table-generators.rst

.. literalinclude:: ../../minpower/tests/uc-WW-5-2/generators.csv

Initial Conditions
-------------------

.. include:: creating-problems-table-initial.rst

.. literalinclude:: ../../minpower/tests/uc-WW-5-2/initial.csv

.. note:
    
    ``hours in status`` denotes the number of hours the generator had been in status at the end of the initial time period.

Loads
---------


.. include:: creating-problems-table-loads.rst

.. literalinclude:: ../../minpower/tests/uc-rolling/loads.csv


Lines
----------

.. include:: creating-problems-table-lines.rst

.. literalinclude:: ../../minpower/tests/opf/lines.csv


Schedules
------------

.. include:: creating-problems-table-schedule.rst

.. literalinclude:: ../../minpower/tests/uc-WW-5-2/load-pattern.csv