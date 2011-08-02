For Researchers
=================

You're probably a researcher or grad student interested in power system optimization. 

**minpower** is a powerful tool even if you just want to use it as a `black box <http://en.wikipedia.org/wiki/Black_box>`_ for solving :doc:`ED <economic-dispatch>`, :doc:`OPF <optimal-power-flow>`, or :doc:`UC <unit-commitment>` problems. Some great built in features include:

* polynomial cost or bid curves
* multi-stage unit commitment
* great visualizations

But where **minpower** really shines is when you want to :ref:`add in a model <add-model>` of an electric vehicle aggregator. Or run a wind farm profitability study where :doc:`UC <unit-commitment>` is just another :ref:`procedure <procedure>` that you need in a long chain of analysis. When you want to do research.

Because **minpower** is written in Python, the code is easy to read and write. Because **minpower** is open source you can use models other people have written and create your own.

.. _procedure:

Calling a procedure
--------------------

    #. Find the procedure you are looking for (use the search box on the sidebar or check the :doc:`documentation`)
    #. Import the procedure into your own script::

        from minpower.solve import create_problem

.. _add-model:

Adding your own model
----------------------

The models in **minpower** are all :ref:`object oriented <object-oriented>`. Check out :mod:`powersystems` for examples of existing models. 
Note the five standard methods:

* :meth:`__init__` creates a new object of that class
* :meth:`add_timevars` sets up the optimization variables
* :meth:`constraints` sets up the optimization constraints (and returns them in a dictionary)
* :meth:`cost` defines a cost (if any) for the time
* :meth:`__str__` defines a :abbr:`unique string (for use in creating constraints, which must have unique names)` representing the object

Then create your own model::
    
    class EV_aggregator(object):
        """an example model of an electric vehicle aggregator"""
        def __init__(
            self,
            number_cars=10,
            per_car_capacity=50,
            index=None
            ):
            """create a new aggregator object"""
            self.update(locals())
        def add_timevars(times):
            """create the aggregator's optimization
               variables for each time here"""
        def constraints():
            """define the aggregator's optimization
               constraints here"""
            return constraintsD
        def cost(time):
            """define the aggregator's cost function here"""
        def __str__(self): 
            """a unique identifier for the aggregator"""
            return 'agg_'+self.index
        #some more methods for the aggregator

.. note:: This section is part of a larger tutorial on creating your own models in **minpower** that is coming soon.

Wishlist
""""""""""""""

* stochastic wind    
* storage
* cascading hydro-systems


Collaboration 
--------------

For collaboration `email Adam <mailto:workwith@adamgreenhall.com>`_.

Help
------

Perhaps you are unfamiliar with Python? Check out :doc:`python-intro` to get up to speed.

Check out `Stackoverflow <http://stackoverflow.com/questions/tagged/python>`_ for general Python help - it's approximately 
one million times better than any other help forum. Hashtag any **minpower** questions you post 
with `#minpower <http://stackoverflow.com/questions/tagged/minpower>`_

