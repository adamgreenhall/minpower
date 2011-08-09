Economic Dispatch
==================

..  toctree::
    :hidden:
    :maxdepth: 1
    
    data-input


:abbr:`ED (Economic Dispatch)` tries to allocate available generation to meet the current system load at lowest cost. The classic text is `Wood & Wollenburg <http://amzn.to/wood-wollenburg>`_.

The problem
------------

..  container:: optimizationproblem
    
    :math:`\min \sum_g C_g(P_g)`
    
    :math:`\mathrm{s.t.}\/ P_{\min (g)} \leq P_g \leq P_{\max (g)} \/ \forall \/ \mathrm{generators}\/(g)`
    
    :math:`\mathrm{s.t.}\/ \sum_g P_{g}= P_{\mathrm{load}}`

In this mathematical formulation generators are indexed by :math:`g`. :math:`P_g` is a generator’s power output and :math:`C_g()` is its cost function. The objective is to minimize the total cost. There are two constraints: 

* each generator must be within its real power limits and 
* total power generated must equal the power consumed by the load.



The basics
-----------

Let's say you have made a folder called ``mydispatch`` and put :ref:`the information <dispatch-inputs-example>`
about your problem in the folder. Then if you run the script::
    
    from minpower import solve
    solve.problem('mydispatch/')

you get a plot:

    .. image:: ./_static/demos/dispatch/dispatch.png
       :width: 500 px

and a spreadsheet:

    .. literalinclude:: ./_static/demos/dispatch/dispatch.csv

These outputs show that the problem's two generators (named ``cheap`` and ``expensive``) are being
dispatched so that their incremental costs (the vertical axis in the plot and ``IC`` in the spreadsheet) are equal.
Each generator's incremental cost curve is shown in the plot, with a dot on its current real power output (``P``). 
Because this is a dispatch each generator is on (``u=True``) unless specified in the input spreadsheet.

These outputs are saved in the ``mydispatch`` folder as ``dispatch.png`` and ``dispatch.csv``.

What's actually going on?
-------------------------

It's easy once you get the hang of it. **minpower** will:
    #. read in your files (see :mod:`get_data`)
    #. set up an optimization problem (see :func:`solve.create_problem`)
    #. send it off to a :doc:`solver<solvers>` (see :func:`optimization.solve`)
    #. show you the results (see :class:`results.Solution_ED`)

**minpower** just looks for the files in the ``mydispatch`` directory that describe the generators and load.

.. _dispatch-inputs-example:

Tell it the specifics of your problem by editing the generator file (``generators.csv``):

    .. literalinclude:: ./_static/demos/dispatch/generators.csv
    
and load file (``loads.csv``):

    .. literalinclude:: ./_static/demos/dispatch/loads.csv

.. note:: For more information about what options you can specify in each spreadsheet see: :doc:`data-input`.
