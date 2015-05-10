import logging
import nose
import numpy as np
import pandas as pd
from minpower.tests.test_utils import istest
from minpower.tests.test_integration import run_case, assert_series_equal, assert_frame_equal
logging.basicConfig(level=logging.ERROR)


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


@istest
def expected_cost_case():
    '''
    ensure that a under-forecast wind case has
    an expected cost > observed cost
    '''
    # this is a short and simple case with 4hrs, but make it into two UC days
    hrs = dict(hours_commitment=2, hours_overlap=0)
    slnD = run_case('expected_observed_cost', deterministic_solve=True, **hrs)

    assert(slnD.expected_cost.sum().sum() > slnD.observed_cost.sum().sum())


@istest
def designed_diff_case():
    '''
    ensure that a simple case designed to produce a more expensive
    deterministic forecast solution has a cheaper perfect forecast
    '''
    # this is a short and simple case with 4hrs, but make it into two UC days
    hrs = dict(hours_commitment=2, hours_overlap=0)
    slnP = run_case('deterministic_perfect_difference', perfect_solve=True, **hrs)
    slnD = run_case('deterministic_perfect_difference', deterministic_solve=True, **hrs)

    assert (slnP.generators_power.sum(axis=1) -
            slnD.generators_power.sum(axis=1) == 0).all()
    assert slnP.observed_cost.sum().sum() < slnD.observed_cost.sum().sum()


@istest
def stochastic_load_shedding():
    '''
    Create a sheddable wind generator and one scenario that requires load shedding.
    Ensure that wind is shed in one scenario but not the other.
    '''

    sln = run_case('stochastic_shedding_case')

    epower = sln.generators_power_scenarios
    load_sched = sln.loads[0].schedule

    assert((epower['s0'].sum(axis=1) < load_sched).all())
    assert((epower['s1'].sum(axis=1) == load_sched).all())


@istest
def stochastic_gen_shedding():
    '''
    Create a sheddable wind generator and one scenario that requires wind shedding.
    Ensure that wind is shed in one scenario but not the other.
    '''

    sln = run_case('stochastic_shedding_wind_case')

    epower = sln.generators_power_scenarios
    load_sched = sln.loads[0].schedule
    load_sched.index = epower.major_axis
    # check that generation meets the load for all scenarios
    assert(epower.sum(axis=2).eq(load_sched, axis=0).all().all())

    # get wind power scenarios
    scenario_values = sln.generators[0].scenario_values.drop(
        'probability', axis=2)
    scenario_values = scenario_values[
        scenario_values.items[0]].T.ix[:len(epower.major_axis) - 1] \
        .set_index(epower.major_axis) \
        .rename(
            columns=dict(zip(range(len(sln.scenarios)), sln.scenarios)))
    # calculate wind shed per scenario
    wind_shed = scenario_values - epower.minor_xs('g0')

    assert_series_equal(
        pd.Series(dict(s0=False, s1=True)),
        (wind_shed > 0).all())

# @istest
# FIXME - disabled test for now


def cvar_objective():
    '''
    Set up an either-or two gen case: g1 cheap, g2 expensive,
    with two wind senarios:
        s0 - high prob., use cheap gen
        s1 - very low prob. (below conf. limit), expensive gen needed

    CVaR should heavily weight the unlikely but more expensive scenario.
    EV must consider it, but weights it less.
    The result should be a more expensive CVaR objective.
    '''
    slnEV = run_case('stochastic_cvar_case')
    slnCV = run_case('stochastic_cvar_case',
                     cvar_weight=1.0,  # very risk averse
                     cvar_confidence_level=0.9999)  # very long tail

    assert(slnCV.objective > slnEV.objective)
#    try:
    assert_frame_equal(slnCV.expected_totalcost, slnEV.expected_totalcost)
#    except:
#        debug_frame_unequal(slnCV.expected_totalcost, slnEV.expected_totalcost)
