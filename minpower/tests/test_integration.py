"""
A selection of integration tests. These are designed to find failures that
the unit tests don't pick up.
"""
import os
import pandas as pd
from nose.tools import istest
from pandas.util.testing import assert_frame_equal

from minpower.solve import solve_problem as solve_dir
from minpower.config import user_config



def basic_checks(sln):
    cost = sln.totalcost_generation
    power = sln.generators_power.ix[cost.index]
    status = sln.generators_status.ix[cost.index]

    # make sure that if status = 0 then power also = 0
    Pcheck = power * status
    assert_frame_equal(Pcheck, power)

    # make sure that if status = 0 then cost also = 0
    Ccheck = cost * status
    assert_frame_equal(Ccheck, cost)

    # make sure that generation meets load (plus any shed)
    shed = sln.load_shed_timeseries
    try: scheduled = sln.power_system.total_scheduled_load()
    except AttributeError: 
        # look up the scheduled load from the timeseries data
        loads = [col for col in \
            sln.store['data_timeseries'].columns if col.startswith('d')]
        scheduled = sln.store['data_timeseries'][loads].sum(axis=1)
    try: scheduled.index = shed.index
    except AssertionError:
        # not the same length due to overlap
        scheduled = scheduled.ix[scheduled.index[:len(shed)]]
        scheduled.index = shed.index

    assert_frame_equal(
        pd.DataFrame(scheduled - shed),
        pd.DataFrame(power.sum(axis=1)))


this_directory = os.path.dirname(__file__)
default_config = user_config.copy()

def run_case(name, basedir=this_directory, **kwds):
    '''
    a programatic way to do (nearly) the same thing
    as calling the minpower script
    (nearly: because prepends basedir to the directory name you are solving)
    '''
    # reset user_config to defaults first
    user_config.update(default_config)
    assert(user_config == default_config)
    user_config.breakpoints = 3 # for speedier testing
    user_config.update(kwds)
    sln = solve_dir(os.path.join(basedir, name))
    basic_checks(sln)
    return sln


@istest
def run_uc():
    run_case('uc')

@istest
def run_uc_rolling():
    run_case('uc-rolling')

@istest
def run_ed():
    run_case('ed')

@istest
def run_opf():
    run_case('opf')