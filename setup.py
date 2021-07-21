# minpower's setup script

# make a new release by using
# seed release --dry-run
# and then
# seed release

from setuptools import setup, find_packages

version_number = open("minpower/__init__.py").read().split('"')[1].rstrip('"')

setup(
    name="minpower",
    version=version_number,
    download_url="https://github.com/adamgreenhall/minpower"
    + "/zipball/v{v}".format(v=version_number),
    entry_points="""
    [console_scripts]
    minpower = minpower.solve:main
    standalone_minpower = minpower.solve:standaloneUC
    scheduler_minpower = minpower.experiments.scheduler_minpower:main
    initial_dispatch = minpower.experiments.get_initial_dispatch:main
    """,
    package_data={
        "minpower.configuration": ["minpower.cfg"],
        "minpower.tests": ["*.csv", "*/*.csv", "*/*/*.csv"],
    },
    install_requires=[
        "pandas>=1.3",
        "pyomo>=6.0",
        "matplotlib>=3.4",
    ],
    dependency_links=[
        "http://github.com/Pyomo/pysp/tarball/v6.0#egg=pysp-1.0",
    ],
    tests_require=["nose", "coverage", "objgraph"],
    # it helps to have seed if you are going to make releases
    # but it is not required for setup
    description="power systems optimization made beautiful",
    author="Adam Greenhall",
    author_email="minpower@adamgreenhall.com",
    url="http://adamgreenhall.github.io/minpower",
    packages=find_packages(),
    keywords=["power systems", "optimization"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
    long_description="""
power systems tools made beautiful
-----------------------------------------

* Solves ED, OPF, and UC problems.
* Problems can be defined in simple spreadsheets.
* Visualizations are created for the answers.
* Many solvers are supported.


* `Full documentation and tutorials <http://adamgreenhall.github.io/minpower>`_
* `Code base <http://github.com/adamgreenhall/minpower>`_

""",
)
