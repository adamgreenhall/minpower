import logging
logging.basicConfig(level=logging.ERROR)

import nose
import numpy as np
from minpower.tests.test_utils import istest
from minpower.tests.test_integration import run_case

mipgap = 0.0001


@istest
def run_basic_checks():
    '''
    solutions should all make sense (cost=0 and power=0 if status=0)
    '''
    run_case('stochastic_short_case', deterministic_solve=True)


@istest
def mock_stochastic():
    '''
    the solution to the stochastic problem with only two scenarios,
    both with values equal to the deterministic forecast and prob=0.5,
    should have a total cost equal (within solver tolerance) to
    the deterministic forecat solution total cost
    '''
    slnS = run_case('stochastic_mock_case',
        scenarios_directory='scenarios/')
    slnD = run_case('stochastic_mock_case',
        deterministic_solve=True)

    costS = slnS.observed_cost.sum().sum()
    costD = slnD.observed_cost.sum().sum()

    diffpercent = np.abs((costS - costD) / costD)
    assert(diffpercent < mipgap)


@istest
def standalone():
    try:
        import tables
    except ImportError:
        raise nose.SkipTest('standalone mode requires pytables')

    slnA = run_case('stochastic_short_case', deterministic_solve=True)
    slnB = run_case('stochastic_short_case', deterministic_solve=True, standalone=True)

    assert(slnA.observed_cost.sum().sum() == slnB.observed_cost.sum().sum())
