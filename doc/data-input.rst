Data Input
===============

There is a huge advantage to putting some distance between your data and your models. This page describes the process of translating between data (in spreadsheets) and the model (Python classes).

:mod:`get_data` takes a directory of :abbr:`spreadsheet files (currently just .csv)` and  handles the process of translating the data into lists of usable :mod:`powersystems` objects --- :class:`~powersystems.Generator`, :class:`~powersystems.Load`, and :class:`~powersystems.Line`. [#f1]_

A simple example is the generators table for a dispatch [#f2]_:

.. literalinclude:: ./_static/demos/dispatch/generators.csv

Field names, found on **the top row of the spreadsheet**, tell :mod:`get_data` that ``cheap`` and ``expensive`` are generator names, and that ``100`` is a maximum power. Then :func:`get_data.build_class_list` maps the data in each row into the object's appropriate attribute as described in the :ref:`generators table below<fields-gens>` - the equivalent of typing the following code::
    
    from minpower.powersystems import Generator
    gen1=Generator(name='cheap', Pmax=100, costcurvestring='200 + 5 * P + .3 P^2')
    gen2=Generator(name='expensive', Pmax=100, costcurvestring='300 + 10 P + .25 P^2 + .005 P^3')
    return [gen1,gen2]

..  note:: 
    
    The field names in a ``csv`` file (the top row) are treated as **case** and **space** insensitive! This means that "``Schedule FiLe``" will be translated to "``schedulefile``". 
    
    Field order does not matter. If fields are left out, the values will be set to the class default. Entries which are left blank for a row of data will be given default values.



==========================
Field Names to Attributes
==========================

Field names have a mapping to :mod:`powersystems` object attributes as described in the tables below. 

.. _fields-gens:

:class:`~powersystems.Generator`
------------------------------------

    =====================    =========================================================
    Field                    Attribute
    =====================    =========================================================
    bus                      :py:attr:`~powersystems.Generator.bus`
    costcurveequation        :py:attr:`~powersystems.Generator.costcurvestring`
    fuelcost                 :py:attr:`~powersystems.Generator.fuelcost`
    heatrateequation         :py:attr:`~powersystems.Generator.heatratestring`
    kind                     :py:attr:`~powersystems.Generator.kind`
    mindowntime              :py:attr:`~powersystems.Generator.mindowntime`
    minuptime                :py:attr:`~powersystems.Generator.minuptime`
    mustrun                  :py:attr:`~powersystems.Generator.mustrun`
    name                     :py:attr:`~powersystems.Generator.name`
    p                        :py:attr:`~powersystems.Generator.power`
    pg                       :py:attr:`~powersystems.Generator.power`
    pmax                     :py:attr:`~powersystems.Generator.Pmax`
    pmin                     :py:attr:`~powersystems.Generator.Pmin`
    power                    :py:attr:`~powersystems.Generator.power`
    rampratemax              :py:attr:`~powersystems.Generator.rampratemax`
    rampratemin              :py:attr:`~powersystems.Generator.rampratemin`
    schedulefilename         :py:attr:`~powersystems.Generator.schedulefilename`
    shutdowncost             :py:attr:`~powersystems.Generator.shutdowncost`
    startupcost              :py:attr:`~powersystems.Generator.startupcost`
    type                     :py:attr:`~powersystems.Generator.kind`
    =====================    =========================================================


	
:class:`~powersystems.Line`
------------------------------------
    
    ==============    ========================================
    Field             Attribute
    ==============    ========================================
    from              :py:attr:`~powersystems.Line.From`
    name              :py:attr:`~powersystems.Line.name`
    pmax              :py:attr:`~powersystems.Line.Pmax`
    to                :py:attr:`~powersystems.Line.To`
    ==============    ========================================


:class:`~powersystems.Load`
------------------------------------	

    =====================    ====================================================
    Field                    Attribute
    =====================    ====================================================
    bidequation              :py:attr:`~powersystems.Load.costcurvestring`
    bus                      :py:attr:`~powersystems.Load.bus`
    costcurveequation        :py:attr:`~powersystems.Load.costcurvestring`
    kind                     :py:attr:`~powersystems.Load.kind`
    name                     :py:attr:`~powersystems.Load.name`
    p                        :py:attr:`~powersystems.Load.P`
    pd                       :py:attr:`~powersystems.Load.P`
    pmax                     :py:attr:`~powersystems.Load.Pmax`
    pmin                     :py:attr:`~powersystems.Load.Pmin`
    schedulefilename         :py:attr:`~powersystems.Load.schedulefilename`
    type                     :py:attr:`~powersystems.Load.kind`
    =====================    ====================================================



=======================
Polynomials
=======================

Polynomials are input as a simple string and become :class:`numpy.poly1d` objects. See :py:func:`bidding.parsePolynomial`.


.. rubric:: Footnotes

.. [#f1] From :class:`~powersystems.Generator`, :class:`~powersystems.Load`, and :class:`~powersystems.Line` objects :mod:`get_data` also creates two additional lists of power system objects: :class:`~powersystems.Bus` and :class:`~schedule.Time`. 

.. [#f2] Don't worry about the format (quotes and delimiters) of the ``csv`` file too much. :func:`~commonscripts.readCSV` uses the very flexible :py:class:`csv.Sniffer` to decipher the format.
