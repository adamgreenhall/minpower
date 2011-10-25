# minpower's setup script

#build using:
#python setup.py sdist

#udpate pypi using:
#python setup.py register
#python setup.py sdist upload


#changelog
#1.1: new minpower script!, better setup! more UC features.  

from distutils.core import setup
setup(
    name = "minpower",
    packages = ["minpower"], #code location
    version = "1.1.0",
    description = "power systems optimization made beautiful",
    author = "Adam Greenhall",
    author_email = "minpower@adamgreenhall.com",
    url = "http://minpowertoolkit.com/",
    download_url = "https://github.com/adamgreenhall/minpower/zipball/v1.1.0",
    keywords = ["power systems","optimization"],
    
    scripts= [
        'scripts/minpower',
        'scripts/remote-minpower',
        ],
    
    install_requires=[
        'coopr',
        'scipy', #numpy install breaks, try scipy instead 
        'matplotlib',
        'networkx',
        'python-dateutil',
        ],
    
    classifiers = [    
        "Development Status :: 4 - Beta",
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

* Solves ED, OPF, and UC problems.
* Problems can be defined in simple spreadsheets. 
* Visualizations for the answers. 
* Many solvers supported.


* `Full documentation and tutorials <http://minpowertoolkit.com>`_
* `Actively developed <http://github.com/adamgreenhall/minpower>`_

"""
)
