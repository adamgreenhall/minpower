"""
A selection of integration tests. These are designed to find failures that
the unit tests don't pick up.
"""
import os
from ipdb import set_trace
from test_utils import *
import pandas as pd
from minpower.solve import solve_problem as solve_dir

from pandas.util.testing import assert_frame_equal

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
    scheduled = sln.power_system.total_scheduled_load()
    scheduled.index = shed.index
    assert_frame_equal(
        pd.DataFrame(scheduled + shed), 
        pd.DataFrame(power.sum(axis=1)))
    
    
    # set_trace()
    
def run_case(name):
    user_config_default = user_config.copy()
    user_config.logging_level = logging.ERROR
    user_config.breakpoints = 3
    basedir = os.path.dirname(__file__)
    sln = solve_dir(os.path.join(basedir, name))
    basic_checks(sln)
    return sln
    
@istest
def run_uc():
    sln = run_case('uc')
    
@istest
def run_uc_rolling():
    sln = run_case('uc-rolling')
    
