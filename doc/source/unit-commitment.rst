Unit Commitment
==================

:abbr:`UC (Unit Commitment)` tries to schedule generation to meet the system load for the next :abbr:`several hours (generally 12 or 24hrs)` at lowest cost. :abbr:`UC (Unit Commitment)`  adds a dimension of time to the :abbr:`ED (Economic Dispatch)` problem, with the additional choice of turning generators on or off. The classic text is `Wood & Wollenburg <http://amzn.to/wood-wollenburg>`_.



The problem
------------

..  container:: optimizationproblem
    
    :math:`\min \sum_t \sum_g C_g(P_{t,g}) + C_{\mathrm{su} (g)}(u_{t,g})`
    
    :math:`\mathrm{s.t.} \; P_{\min (g)} \leq P_{t,g} \leq P_{\max (g)}  \; \forall  \; t,g  \; \mathrm{where}  \; u_{t,g}=1`
    
    :math:`\mathrm{s.t.} \; \sum_g P_{t,g}= P_{\mathrm{load}(t)}  \; \forall  \; t`
    
    :math:`\mathrm{s.t.} \; P_{\mathrm{ramp min} (g)} \leq P_{t,g}-P_{t-1,g} \leq P_{\mathrm{ramp max} (g)}    \; \forall  \; t,g`

In this mathematical formulation generators are indexed by :math:`g` and time is indexed by :math:`t`. :math:`P_{t,g}` is a generator’s power output at time :math:`t` and :math:`u_{t,g}` is its operation status (on/off). :math:`C_g()` is the generator's production cost function and :math:`C_{\mathrm{su} (g)}()` is its startup/shutdown cost. The objective is to minimize the total cost. The constraints are: 

* each generator must be within its real power limits
* total power generated must equal the power consumed by the load
* each generator must be within its real power :abbr:`ramping (think acceleration in a car - you can't go from 0-60mph in one second. Similarly most generators cannot change their power output too quickly.)` limits
* each generator must be within its :abbr:`up/down time limits (Nuclear and coal plants generally have especially long power up and cool down time constraints.)`

.. note:: The last constraint is not shown in the formulation above :abbr:`due to complexity (it is a pain to show mathematically and is confusing to read. If you are interested, see the formulation used in the code.)`. For the actual formulation in use, see :meth:`powersystems.Generator.create_constraints`.

Example Problem
-----------------

To define a simple :abbr:`UC (Unit Commitment)` problem, **Minpower** requires at least three spreadsheets. The first describes the generator parameters (`generators.csv <https://github.com/adamgreenhall/minpower/blob/master/minpower/tests/uc-WW-5-2/generators.csv>`_):

.. literalinclude:: ../../minpower/tests/uc-WW-5-2/generators.csv

The second simply describes which loads exist on the system and where there schedule files are (`loads.csv <https://github.com/adamgreenhall/minpower/blob/master/minpower/tests/uc-WW-5-2/loads.csv>`_):

.. literalinclude:: ../../minpower/tests/uc-WW-5-2/loads.csv

The other spreadsheets describe the load (or non-controllable generation) energy schedules. In this case (`load-pattern.csv <https://github.com/adamgreenhall/minpower/blob/master/minpower/tests/uc-WW-5-2/load-pattern.csv>`_): 

.. literalinclude:: ../../minpower/tests/uc-WW-5-2/load-pattern.csv

.. note:: For more information about what options you can specify in each spreadsheet see: :doc:`creating-problems`.

Solving
---------

Save the two spreadsheets above into into a folder (call it ``mycommitment``) and run::
    
    minpower mycommitment

This particular problem is also **Minpower** built-in test case (based on `Wood & Wollenburg <http://amzn.to/wood-wollenburg>`_ Problem 5.2), so if you haven't been following along, to solve it, call::

    minpower uc-WW-5-2

Example Solution
-------------------

The result is a plot (``commitment.png``):

    .. image:: ./_static/demos/commitment/commitment.png
       :width: 500 px

This figure has two axes that share the same time axis. The top axes shows the :abbr:`price of energy (The system price is generally determined by the dual of the energy constraint in the optimization problem and is in $/MWh.)` for the system. The bottom axes shows the energy that each generator produces. 

.. note:: For only a few generators, :meth:`results.Solution_UC.vizualization` displays a stack plot showing power for each generator. For more generators, the display is grouped by :attr:`~powersystems.Generator.kind` (so that all the coal plants as one color, all the wind as another color, ...).

For this example we have two generators, one named ``cheap`` (which produces energy for $45/MWh) and one named ``expensive`` (which produces energy for $150/MWh). Obviously we only turn on the expensive generator after we can't use the cheaper any more (its limit is 100MW for this example). So as the load goes up and over 100MW, the expensive generator is committed.

But why doesn't the expensive generator turn back off at 6:00, when the load goes back down? It can't turn off that quickly - it has a minimum up time of 2hrs and a minimum output of 20MW. But why does the price go back down? It's complicated [#f1]_. 


The data from the graph is also output in spreadsheet form (``commitment.csv``):

    .. literalinclude:: ../../minpower/tests/uc-WW-5-2/commitment.csv

Unlike :doc:`ED <economic-dispatch>` and :doc:`OPF <optimal-power-flow>` results, this spreadsheet is not particularly easy to read. It is meant more for machines than for humans. The spreadsheet gives status and energy output for each generator, along with the system energy price, for each time.

.. rubric:: Footnotes


.. [#f1] Generators at their limits can't set the price. In the real world the monetary differences are dealt with via a system called "side payments". In the example above a side payment of $105/MWh would be made to the more expensive generator for its second hour to make sure that it recovers its cost of operating for that hour.
