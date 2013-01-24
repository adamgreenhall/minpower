For Researchers
=================

You're probably a researcher or grad student interested in power system optimization. 

**Minpower** is a powerful tool even if you just want to use it as a `black box <http://en.wikipedia.org/wiki/Black_box>`_ for solving :doc:`ED <economic-dispatch>`, :doc:`OPF <optimal-power-flow>`, or :doc:`UC <unit-commitment>` problems. Some great built in features include:

* polynomial cost or bid curves
* rolling unit commitments
* great visualizations

But where **Minpower** really shines is when you want to :ref:`add a constraint<add-constraint>` like load shedding, or even :ref:`add a model <add-model>` of an electric vehicle aggregator. Or run a wind farm profitability study where :doc:`UC <unit-commitment>` is just another :ref:`procedure <procedure>` that you need in a long chain of analysis. When you want to do research.

Because **Minpower** is written in Python, the code is easy to read and write. Because **Minpower** is open source you can use models other people have written and create your own.

.. _procedure:

Calling a procedure
--------------------

    Minpower doesn't have a true API - it has been developed primarily as a research tool. But that doesn't mean you can't take only the pieces you need out of it. You can import any function (or class) into your own script, e.g.::

        from minpower.solve import create_problem

    and then call it, e.g.::
        
        create_problem(power_system=my_ERCOT_iso_model, times=year_2010_hourly_times)

    Checking out how Minpower's `testing utilities <https://github.com/adamgreenhall/minpower/blob/master/minpower/tests/>`_ work is one way to see how you can programmatically create/change/solve/test problems.


.. _add-constraint:

Adding a constraint
--------------------
    
Constraints can be added to existing power system components with a very simple syntax. Within the :meth:`~optimization.OptimizationObject.create_constraints` method (e.g. :meth:`~powersystems.Generator.create_constraints`), simply call :meth:`~optimization.OptimizationObject.add_constraint`. This method takes a name for the constraint, a time the constraint is in reference to (if applicable), and an expression. As an example, the maximum power limit is set for a generator by ::
    
    class Generator(OptimizationObject):
        #other methods here
        def create_constraints(self,times):
            for time in times:
                #add other constraints here
                expression = self.power(time)<=self.status(time)*self.Pmax
                self.add_constraint('max gen power', time, expression) 
            return self.all_constraints(times)


.. _add-model:

Adding a component
-------------------

The power system components in **Minpower** are :ref:`object oriented <object-oriented>` models and are also all :class:`~optimization.OptimizationObject`s. Check out :mod:`powersystems` for examples of existing models. To define your own, simply inherit the :class:`~optimization.OptimizationObject` class and follow its template: 

    * :meth:`__init__` creates a new object of that class and sets its parameters
    * :meth:`~optimization.OptimizationObject.init_optimization` is called within :meth:`__init__` and sets up an empty structure for optimization variables, constraints, and objective components
    * :meth:`~optimization.OptimizationObject.create_variables` sets up the optimization variables
    * :meth:`~optimization.OptimizationObject.create_constraints` sets up the optimization constraints
    * :meth:`~optimization.OptimizationObject.create_objective` defines a objective cost component (if any)
    * :meth:`__str__` defines a :abbr:`unique string (for use in creating variables and constraints, which must have unique names)` representing the object

Below is an example of the basic structure for an EV aggregator model::
    
    class EV_aggregator(OptimizationObject):
        """an example model of an electric vehicle aggregator"""
        def __init__(
            self,
            number_cars=10,
            per_car_capacity=50,
            index=None  ):
            """create a new aggregator object"""
            update_attributes(self,locals()) #load in inputs
            self.init_optimization()
        def create_variables(times):
            """create the aggregator's optimization
               variables for each time here"""
            return self.all_variables(times)
        def create_objective(time):
            """define the aggregator's cost function here"""
            return self.objective
        def create_constraints():
            """define the aggregator's optimization
               constraints here"""
            return self.all_constraint(times)
        #some more methods for the aggregator
        def __str__(self): 
            """a unique identifier for the aggregator"""
            return 'agg_'+self.index
        

Wishlist
""""""""""""""

* demand response
* storage
* cascading hydro-systems


Collaboration 
--------------

For collaboration get in touch with Adam via `email <mailto:argreen@uw.edu>`_ or `@adamgreenhall <http://twitter.com/adamgreenhall>`_.

Help
------

Perhaps you are unfamiliar with Python? Check out :doc:`python-intro` to get up to speed.

Check out `Stackoverflow <http://stackoverflow.com/questions/tagged/python>`_ for general Python help. 

If you find a bug, please report it on the `GitHub issue tracker <https://github.com/adamgreenhall/minpower/issues>`_.