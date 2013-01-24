Intro to Python
=========================

**minpower** takes advantage of many of Python_'s great features. If you have not worked with Python_ much this is a quick tutorial to help you understand what is going on in the code. 

Syntax
--------
Readability is critical, so no curly braces ``{}`` are used in Python. Instead code is :abbr:`indented (using 4 spaces per indent)` to show loops, functions, ...

List comprehension
------------------
Lists are basically arrays, but smarter::

    >>> timesL=['1:00','2:00','3:00']
    >>> for time in timesL: print time
    1:00
    2:00
    3:00


Dictionaries
--------------
Dictionaries create one-to-one mappings, just what you would expect from the name::

    >>> alphabetD=dict(a=1,b=2,c=3)
    >>> print alphabetD['a']
    1
    >>> print alphabetD['b']
    2



Key Word Arguments
--------------------
Order does not matter. Defaults can be set. This can be really beautiful::

    >>> def f(a=0,b=2): return a+b
    >>> print f(), f(a=4), f(b=3), f(a=-1,b=2), f(b=3,a=4)
    2 6 3 1 7

.. _object-oriented:


Object Oriented
-----------------------
Classes basically create a fixed set of ``attributes`` (properties) and ``methods`` (functionality). Objects of a certain class kind are called ``class instances``. Instances are created via the classes name, with setup via the class's :py:meth:`~object.__init__` method: :: 
    
    class Generator(object):
        """describes a generator"""
        def __init__(self,Pmin=0,Pmax=500, kind='coal'):
            #add attributes to class from inputs
            self.update(locals()) 
        def operating_range(self):
            """the power range of the generator"""
            return self.Pmax-self.Pmin
        #other methods here

So in practice this would look like::

    >>> plantA = Generator(Pmin=10,Pmax=100)
    >>> print plantA.Pmin, plantA.kind, plantA.operating_range()
    10 'coal' 90

.. _Python: http://python.org

