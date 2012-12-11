from vbench.benchmark import Benchmark

SECTION = 'Unit commitment'

common_setup = """
from minpower_benchmark_utils import *
"""


setup = common_setup + """
directory = '~/minpower/minpower/tests/uc'
"""
statement = """
solve_problem(directory,
    shell=False,
    problemfile=False,
    csv=False)
"""

bm_simple_uc = Benchmark(statement, setup, ncalls=1,
                       name='simple_uc')
