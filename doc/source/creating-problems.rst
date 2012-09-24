Creating a Problem
====================

Minpower solves problems that are defined in spreadsheets. The most basic :abbr:`ED (Economic Dispatch)` problem only has two files: ``generators.csv`` and ``loads.csv``. If you are solving an :abbr:`UC (Unit Commitment)` then you need to define the initial conditions for your generation in ``initial.csv``. Scheduled or predicted energy amounts (e.g. predicted wind farm output or predicted load demand) over a series of times can be specified in a file defined by the ``schedule file name`` column of the component. If you are solving an :abbr:`OPF (Optimal Power Flow)`, then you also need to define your transmission lines in ``lines.csv``.

The following tables give details on how to describe each component using spreadsheet columns. (Column order does not matter. Capitalization and spaces are ignored in the header row.) Examples spreadsheets are given after each table.

Generators
-----------

+-----------------------+----------------------------------------------------+--------------+-------------+
| Column Name           | Description                                        | Default      | Units       |
+-----------------------+----------------------------------------------------+--------------+-------------+
| name                  | generator name                                     |              |             |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Power min             |                                                    | 0            | MW          |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Power max             |                                                    | 500          | MW          |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Cost curve equation   | fuel cost polynomial                               |              | $/MWh       |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Heat rate equation    | heat rate polynomial                               |              | MMBtu/MWh   |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Fuel cost             |                                                    | 1            | $/MMBtu     |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Start up cost         |                                                    | 0            | $           |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Shut down cost        |                                                    | 0            | $           |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Ramp rate min         |                                                    |              | MW/h        |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Ramp rate max         |                                                    |              | MW/h        |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Must run              | gen. status must remain ON                         | 0            |             |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Schedule filename     | filename of spreadsheet describing gen. schedule   |              |             |
+-----------------------+----------------------------------------------------+--------------+-------------+
| Bus                   | name of bus where gen. is connected                | single bus   |             |
+-----------------------+----------------------------------------------------+--------------+-------------+


.. literalinclude:: ../minpower/tests/uc-WW-5-2/generators.csv

Initial Conditions
-------------------

+-------------------+-----------------------------------+-----------------+---------+
| Column Name       | Description                       | Default         | Units   |
+-------------------+-----------------------------------+-----------------+---------+
| name              | generator name                    |                 |         |
+-------------------+-----------------------------------+-----------------+---------+
| power             | output at initial time            | (Pmax-Pmin)/2   | MW      |
+-------------------+-----------------------------------+-----------------+---------+
| status            | status (1 or 0) at initial time   | 1               |         |
+-------------------+-----------------------------------+-----------------+---------+
| hours in status   |                                   | 100             | hrs     |
+-------------------+-----------------------------------+-----------------+---------+

.. literalinclude:: ../minpower/tests/uc-WW-5-2/initial.csv

.. note:
    
    ``Hours in status`` denotes the number of hours the generator had been in status at the end of the initial time period.

Loads
---------

+---------------------+----------------------------------------------------------------------+--------------+---------+
| Column Name         | Description                                                          | Default      | Units   |
+---------------------+----------------------------------------------------------------------+--------------+---------+
| name                | load name                                                            |              |         |
+---------------------+----------------------------------------------------------------------+--------------+---------+
| power               | load power (a single number for ED problems or base load)            |              | MW      |
+---------------------+----------------------------------------------------------------------+--------------+---------+
| schedule filename   | spreadsheet filename describing the predicted load power over time   |              |         |
+---------------------+----------------------------------------------------------------------+--------------+---------+
| Bus                 | name of bus where load is connected                                  | single bus   |         |
+---------------------+----------------------------------------------------------------------+--------------+---------+

.. literalinclude:: ../minpower/tests/uc-rolling/loads.csv


Lines
----------

+---------------+--------------------------------------+-----------+---------+
| Column Name   | Description                          | Default   | Units   |
+---------------+--------------------------------------+-----------+---------+
| name          | line name                            |           |         |
+---------------+--------------------------------------+-----------+---------+
| to            | name of bus where line originates    |           |         |
+---------------+--------------------------------------+-----------+---------+
| from          | name of bus where line terminates    |           |         |
+---------------+--------------------------------------+-----------+---------+
| reactance     | total electrical reactance of line   | 0.05      | p.u.    |
+---------------+--------------------------------------+-----------+---------+
| P max         | maximum power limit of line          |           | MW      |
+---------------+--------------------------------------+-----------+---------+

.. literalinclude:: ../minpower/tests/opf/lines.csv


Schedules
------------

+---------------+-------------------------------------------------------------+-----------+---------+
| Column Name   | Description                                                 | Default   | Units   |
+---------------+-------------------------------------------------------------+-----------+---------+
| time          | time and date (if applicable) for the start of the period   |           |         |
+---------------+-------------------------------------------------------------+-----------+---------+
| power         | energy scheduled (or predicted) for the period              |           | MWh     |
+---------------+-------------------------------------------------------------+-----------+---------+

.. literalinclude:: ../minpower/tests/uc-WW-5-2/load-pattern.csv