# minpower's setup script
# build using
# python setup.py sdist bdist_wininst

# need to install python-dev package to build windows installer
from distutils.core import setup
setup(
    name = "minpower",
    packages = ["minpower"], #code location
    version = "0.0.1",
    description = "power systems optimization made beautiful",
    author = "Adam Greenhall",
    author_email = "minpower@adamgreenhall.com",
    url = "http://adamgreenhall/minpower",
    download_url = "http://adamgreenhall/minpower/minpower-0.0.1.tgz",
    keywords = ["power systems","optimization",""],
    classifiers = [    
        "Development Status :: 3 - Alpha",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",      
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",    
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Mathematics",
        ],
    long_description = """\
power systems tools made beautiful
-----------------------------------------

*. Solves :abbr:`ED (Economic Dispatch)`, :abbr:`OPF (Optimal Power Flow)`, and :abbr:`UC (Unit Commitment)` problems.
*. Problems can be defined in simple spreadsheets. 
*. Visualizations for the answers. 
*. Many `solvers <http://adamgreenhall.com/minpower/solvers>`_ supported.

*. `Full documentation and tutorials<http://adamgreenhall.com/minpower>`_
*. Actively developed on `GitHub <http://github.com/adamgreenhall/minpower>`_.

"""
)
