Economic Dispatch
==================

:abbr:`ED (Economic Dispatch)` tries to allocate available generation to meet the current system load at lowest cost. The classic text is `Wood & Wollenburg <http://amzn.to/wood-wollenburg>`_.

The problem
------------

..  container:: optimizationproblem
    
    :math:`\min \sum_g C_g(P_g)`
    
    :math:`\mathrm{s.t.}  P_{\min (g)} \leq P_g \leq P_{\max (g)}   \forall   \mathrm{generators} (g)`
    
    :math:`\mathrm{s.t.}  \sum_g P_{g}= P_{\mathrm{load}}`

In this mathematical formulation generators are indexed by :math:`g`. :math:`P_g` is a generator’s power output and :math:`C_g()` is its cost function. The objective is to minimize the total cost. There are two constraints: 

* each generator must be within its real power limits and 
* total power generated must equal the power consumed by the load.

Example Problem
-----------------

To define a simple :abbr:`ED (Economic Dispatch)` problem, **Minpower** requires two spreadsheets. The first describes the generator parameters (`generators.csv <https://github.com/adamgreenhall/minpower/blob/master/minpower/tests/ed-WW-3-7/generators.csv>`_):

.. literalinclude:: ../minpower/tests/ed-WW-3-7/generators.csv

The second simply describes the load (`loads.csv <https://github.com/adamgreenhall/minpower/blob/master/minpower/tests/ed-WW-3-7/loads.csv>`_):

.. literalinclude:: ../minpower/tests/ed-WW-3-7/loads.csv

.. note:: For more information about what options you can specify in each spreadsheet see: :doc:`creating-problems`.

Solving
---------

Save the two spreadsheets above into into a folder (call it ``mydispatch``) and run::
    
    minpower mydispatch

This particular problem is also **Minpower** built-in test case (based on `Wood & Wollenburg <http://amzn.to/wood-wollenburg>`_ Problem 3.7), so if you haven't been following along, to solve it, call::

    minpower ed-WW-3-7

Example Solution
-------------------

The result is a plot (``dispatch.png``):

    .. image:: ../minpower/tests/ed-WW-3-7/dispatch.png
       :width: 500 px

and a spreadsheet (``dispatch.csv``):

    .. literalinclude:: ../minpower/tests/ed-WW-3-7/dispatch.csv

These outputs show that the problem's two generators (named ``cheap`` and ``expensive``) are being
dispatched so that their incremental costs (the vertical axis in the plot and ``IC`` in the spreadsheet) are near equal. 
Each generator's linearized incremental cost is shown in the plot, with a dot on its current real power output (``P``). 
Because this is a dispatch each generator is on (``u=True``) unless specified in the input spreadsheet.