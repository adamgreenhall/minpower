# minpower's setup script

# make a new release by using 
# seed release --dry-run
# and then 
# seed release

from setuptools import setup, find_packages

version_number = open('minpower/__init__.py').read().split('"')[1].rstrip('"')

setup(
    name = "minpower",
    version = version_number,
    download_url = "https://github.com/adamgreenhall/minpower" + \
        "/zipball/v{v}".format(v=version_number),
    entry_points="""
    [console_scripts]
    minpower = minpower.solve:main
    standalone_minpower = minpower.solve:standaloneUC
    hyak_minpower = minpower.experiments.minpower_hyak:main
    """,

    package_data={
        'minpower.configuration': ['minpower.cfg'],
        'minpower.tests': [
            '*.csv', 
            '*/*.csv',
            '*/*/*.csv']},

    install_requires=[
        'Coopr>=3.2.6148', #3.1.5409
        'coopr.core>=1.0',
        'pyutilib>=4.0',
        'numpy>=1.6.1',
        'pandas>=0.10',
        'python-dateutil>=1.4.1',
        'ordereddict>=1.1',
        'PyYAML>=3.10',
    ],
    tests_require=[
        'nose',
        'coverage',
        'objgraph'
        ],
    
    # it helps to have seed if you are going to make releases
    # but it is not required for setup
    # setup_requires=['seed >= 0.2.12'],

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
    long_description = """
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