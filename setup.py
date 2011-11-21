# minpower's setup script

#build using:
#python setup.py sdist

#udpate pypi using:
#python setup.py register
#python setup.py sdist upload
#git tag -a v2.0 -m 'version 2.0'; git push --tags
#info: http://packages.python.org/distribute/setuptools.html#basic-use


#changelog
#1.1: new minpower script, better setup, more UC features.  

from setuptools import setup, find_packages
setup(
    name = "minpower",
    version = "2.0",
    download_url = "https://github.com/adamgreenhall/minpower/zipball/v2.0",

    scripts= [
        'scripts/minpower',
        'scripts/remote-minpower',
        ],
    install_requires=[
        'Coopr>=3.0.4362',
        'matplotlib>=1.0.1',
        'networkx>=1.5',
        'scipy>=0.9',
        'ordereddict>=1.1',
        'progressbar>=2.3',
        'python-dateutil>=1.4.1',
    ],
    tests_require=['Attest>=0.5.2'],

    description = "power systems optimization made beautiful",
    author = "Adam Greenhall",
    author_email = "minpower@adamgreenhall.com",
    url = "http://minpowertoolkit.com/",

    packages = find_packages(),
    keywords = ["power systems","optimization"],
    
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
* Visualizations are created for the answers. 
* Many solvers are supported.


* `Full documentation and tutorials <http://minpowertoolkit.com>`_
* `Actively developed <http://github.com/adamgreenhall/minpower>`_

"""
)
