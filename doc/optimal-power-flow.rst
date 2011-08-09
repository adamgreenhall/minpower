Optimal Power Flow
=====================


:abbr:`OPF (Optimal Power Flow)` tries to allocate available generation to meet the current load while keeping transmission lines within :abbr:`the limits (governed in reality by stability and sag concerns)` of what they can carry. :abbr:`OPF (Optimal Power Flow)` adds a dimension of space to the :abbr:`ED (Economic Dispatch)` problem. Currently **minpower** performs the simplest version of power flow, called decoupled :abbr:`OPF (Optimal Power Flow)` and considers only real power [#f1]_. The classic text is `Bergen & Vittal <http://bitly.com/bergen-vittal>`_.

..  toctree::
    :hidden:
    :maxdepth: 1
    
    data-input

The problem
------------

..  container:: optimizationproblem
    
    :math:`\min \sum_g C_g(P_g)`
    
    :math:`\mathrm{s.t.}\/ P_{\min (g)} \leq P_g \leq P_{\max (g)} \/ \forall \/ \mathrm{generators}\/(g)`
    
    :math:`\mathrm{s.t.}\/ P_{\mathrm{gen} (i)} - P_{\mathrm{load} (i)} - \sum_j P_{ij} = 0  \/ \forall \/ \mathrm{buses}\/(i)`
    
    :math:`\mathrm{s.t.}\/ P_{\min (ij)} \leq P_{ij} \leq P_{\max (ij)} \forall \/ \mathrm{lines}\/(ij)`

In this mathematical formulation generators are indexed by :math:`g`. :math:`P_g` is a generator’s power output and :math:`C_g()` is its cost function. The objective is to minimize the total cost. There are three constraints: 

* each generator must be within its real power limits
* :abbr:`inflow must equal outflow (called power balance)` at each bus
* each line must be within its real power limits

For :abbr:`DCOPF (De-Coupled Optimal Power Flow)`, the real power flow on a line :math:`P_{ij} = \frac{1}{X_{ij}} \left( \theta_i-\theta_j \right)` depends linearly on the voltage angles of the buses it connects (:math:`\theta_{i}`, :math:`\theta_{j}`) and its own reactance :math:`X_{ij}`. Bus angles are the difference in voltage angle between the bus and the :abbr:`reference bus (known as the swing or slack bus)` which has angle :math:`0\degree`. 





The basics
-------------

Let's say you have made a folder called ``mypowerflow`` and put :ref:`the information <powerflow-inputs-example>`
about your problem in the folder. Then if you run the script::
    
    from minpower import solve
    solve.problem('mypowerflow/')

:abbr:`OPF (Optimal Power Flow)` is difficult to visualize (please `send suggestions <mailto:minpower@adamgreenhall.com>`_), but here is what **minpower** creates:

    .. image:: ./_static/demos/powerflow/powerflow.png
       :width: 500 px

* A red colored transmission line indicates a limit on that line, while gray lines are below their limits. *The Tacoma* :math:`\rightarrow` *Seattle line is at its limit. The other two gray colored lines are running below their limits.* 
* The width of the line indicates the amount of power flow. *The Olympia-Seattle line has the largest flow*. 
* The :abbr:`stubs (arrows would be nicer, but this is what networkx gives)` at one end indicate direction of flow. *Flow direction is Olympia* :math:`\rightarrow` *Seattle*. 
* :abbr:`Injected power (generation minus load for the bus)` is shown by the color of the bus. *Olympia is injecting power into the system while Seattle is pulling power*. 

There are also spreadsheet outputs of generator and line information:

    .. literalinclude:: ./_static/demos/powerflow/powerflow-generators.csv

Each generator's real power output (``P``) and incremental cost (``IC``) is output. 
Because this is a power flow each generator is on (``u=True``) unless specified in the input spreadssheet.

    .. literalinclude:: ./_static/demos/powerflow/powerflow-lines.csv

Each line's real power flow is output. Lines that have congestion will show a positive shadow price. 
*Because the flow is Tacoma* :math:`\rightarrow` *Seattle and the from/to fields of the
spreadsheet are the other way around, we see a negative power flow. The Seattle-Tacoma
line is at its limit, so there is an extra cost to the system from the congestion and the line has a
positive shadow price.*



These outputs are saved in the ``mypowerflow`` folder as ``powerflow.png``, ``powerflow-generators.csv``, and ``powerflow-lines.csv``.

What's actually going on?
-------------------------


It's easy once you get the hang of it. **minpower** will:
    #. read in your files (see :mod:`get_data`)
    #. set up an optimization problem (see :func:`solve.create_problem`)
    #. send it off to a :doc:`solver<solvers>` (see :func:`optimization.solve`)
    #. show you the results (see :class:`results.Solution_OPF`)

**minpower** just looks for the files in the ``mypowerflow`` directory that describe the generators, loads, and lines.

.. _powerflow-inputs-example:

Tell it the specifics of your problem by editing the generator file (``generators.csv``):

    .. literalinclude:: ./_static/demos/powerflow/generators.csv
    
the loads file (``loads.csv``):

    .. literalinclude:: ./_static/demos/powerflow/loads.csv

the lines file (``lines.csv``):
    
    .. literalinclude:: ./_static/demos/powerflow/lines.csv
    
.. note:: For more information about what options you can specify in each spreadsheet see: :doc:`data-input`.





.. rubric:: Footnotes
 
.. [#f1] Modern power systems often have reactive power issues. While :abbr:`DCOPF (Decoupled Optimal Power Flow)` is a decent approximate solution with reactive power considered, your results may vary significantly from reality without it.

