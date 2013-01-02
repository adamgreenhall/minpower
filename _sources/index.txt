power systems tools made beautiful
====================================

**Minpower** is an open source toolkit for 
:doc:`students<students>` and :doc:`researchers<researchers>` in power systems.
It is designed to make working with :doc:`ED <economic-dispatch>`,
:doc:`OPF <optimal-power-flow>`, and :doc:`UC <unit-commitment>` problems
:doc:`simple and intuitive<why-minpower>`. The goal is to foster :doc:`collaboration<collaborate>`
with other :doc:`researchers<researchers>` and to make learning easier for :doc:`students<students>`.

.. container:: solution-homepage     
    
    To solve a problem:
    
        ``minpower mycommitment/``
    

..  container:: installation-homepage

    Installation:

    * ``pip install minpower``
    * use with your favorite solver


**Minpower** creates great visualizations too, like this one for :doc:`UC <unit-commitment>`:
    
    ..  image:: ./_static/commitment-demo.png
        :width: 500 px

Some recent talks and publications:

- `paper preprint for PES2012 <http://minpowertoolkit.com/minpower.pdf>`_
- `a talk at Alstom-Grid <http://minpowertoolkit.com/talk-2012-03-08-alstom.pdf>`_
- `an introduction for the Wind Integration Research Lab <http://minpowertoolkit.com/talk-2011-10-11-wirl/>`_
- `an interactive display demo of an ERCOT simulation <http://minpower-ercot-2010.heroku.com/>`_




.. toctree::
    :maxdepth: 3
    
    why-minpower
    install

.. toctree::

    basic-use
    creating-problems
    configuration
    
.. toctree::
    
    students
    researchers

.. toctree::
    
    economic-dispatch
    optimal-power-flow
    unit-commitment
    
.. toctree::
    :maxdepth: 2
    
    api/index

.. toctree::
    
    collaborate
    about
