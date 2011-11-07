Creating a Problem
====================

Minpower solves problems that are defined in spreadsheets. The most basic :abbr:`ED (Economic Dispatch)` problem only has two files: ``generators.csv`` and ``loads.csv``. If you are solving an :abbr:`UC (Unit Commitment)` then you need to define the initial conditions for your generation in ``initial.csv``. If you are solving an :abbr:`OPF (Optimal Power Flow)`, then you also need to define your transmission lines in ``lines.csv``. 

The following tables give details on how to describe each component using spreadsheet columns. (Order does not matter. Capitalization is ignored.)

Generators
-----------
.. |Column Name|Description|Default|Units|
.. |name|generator name| | |
.. |Power min| |0|MW|
.. |Power max| |500|MW|
.. |Ramp rate min| | |MW/h|
.. |Ramp rate max| | |MW/h|
.. |Start up cost| | 0 |$|
.. |Shut down cost| | 0 |$|
.. |Cost curve equation|a polynomial describing the generators cost curve| |$/MWh|
.. |Heat rate equation|a polynomial describing the generators heat rate curve, an alternate formulation to the cost curve when used with the fuel cost parameter| |MMBtu/MWh|
.. |Fuel cost| |1 |$/MMBtu|
.. |Must run|flag to specify that the unit must have an ON status|0| |
.. |Schedule filename|spreadsheet filename describing the non-controllable generator's schedule| | |

Loads
---------

Initial Conditions
-------------------

Lines
----------
