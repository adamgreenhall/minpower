Python Packages
================


Python packages are open source add-ons that provide great functionality not included in the Python core. 
They can be installed from the command line by using a package manager like
`pip <http://pypi.python.org/pypi/pip>`_ (or ``pypm`` if you are
using `ActivePython <http://activestate.com/activepython>`_).

For example::

    pip install matplotlib

..  note:: On Mac/Linux systems you will need to run these commands as root (``sudo pip ...``)

You can get all the **minpower**-required packages by running::

    pip install pulp coopr numpy matplotlib networkx minpower

An individual package can also be installed by downloading it from the Python `package index <http://pypi.python.org/pypi>`_ and then running::
    
    cd download_directory
    python setup.py install

You can also download the most recent source of **minpower** from `Github <http://github.com/adamgreenhall/minpower>`_ and install that as above.


================     ===================================
Package              Use in minpower
================     ===================================
pulp                 optimization (current)
coopr                optimization (future)
numpy                matrix and polynomial math
matplotlib           visualization
networkx             visualization of graphs (for OPF)
dateutil             parses dates and times
================     ===================================

.. note:: If you are using Mac OSX and are having trouble with installing ``matplotlib`` through ``pip`` - this is a common issue. Check out the `matplotlib installation instructions <http://matplotlib.sourceforge.net/users/installing.html>`_ for your options.

