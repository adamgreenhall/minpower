"""
A selection of integration tests. These are designed to find failures that
the unit tests don't pick up.
"""
import os
import nose
from nose.tools import istest
from pandas.util.testing import assert_frame_equal, assert_series_equal

from minpower.solve import solve_problem as solve_dir
from minpower.config import user_config
from .test_utils import reset_config, with_setup


def basic_checks(sln):
    cost = sln.totalcost_generation
    power = sln.generators_power.loc[cost.index]
    status = sln.generators_status.loc[cost.index]

    # make sure that if status = 0 then power also = 0
    Pcheck = power * status
    assert_frame_equal(Pcheck, power)

    # make sure that if status = 0 then cost also = 0
    Ccheck = cost * status
    assert_frame_equal(Ccheck, cost)

    # make sure that generation meets load (plus any shed)
    shed = sln.load_shed_timeseries
    try:
        scheduled = sln.power_system.total_scheduled_load()
    except AttributeError:
        # look up the scheduled load from the timeseries data
        loads = [
            col for col in sln.store["data_timeseries"].columns if col.startswith("d")
        ]
        scheduled = sln.store["data_timeseries"][loads].sum(axis=1)
    try:
        scheduled.index = shed.index
    except AssertionError:
        # not the same length due to overlap
        scheduled = scheduled.loc[scheduled.index[: len(shed)]]
        scheduled.index = shed.index

    assert_series_equal(scheduled - shed, power.sum(axis=1))


#    except:
#        wind_gen = sln.power_system.get_generator_with_observed()
#        gen_scheduled = pd.DataFrame(dict(
#            wind_obs=wind_gen.observed_values,
#            other_sched=sum(gen.schedule \
#                for gen in sln.power_system.generators() \
#                if not gen.is_controllable and gen != wind_gen)
#            )).loc[:len(shed.index)]
#        gen_scheduled.index = shed.index
#
#        print('controllable_requirement')
#        print(scheduled - gen_scheduled.sum(axis=1))
#        raise


this_directory = os.path.dirname(__file__)
default_config = user_config.copy()


def run_case(name, basedir=this_directory, **kwds):
    """
    a programatic way to do (nearly) the same thing
    as calling the minpower script
    (nearly: because prepends basedir to the directory name you are solving)
    """
    # reset user_config to defaults first
    user_config.update(default_config)
    assert user_config == default_config
    user_config.breakpoints = 3  # for speedier testing
    user_config.update(kwds)
    sln = solve_dir(os.path.join(basedir, name))
    basic_checks(sln)
    return sln


@istest
def run_uc():
    run_case("uc")


@istest
def run_uc_rolling():
    run_case("uc-rolling")


@istest
def run_ed():
    run_case("ed")


@istest
def run_opf():
    run_case("opf")


# just test that the visulizations all work
# if matplotlib is installed
@istest
@with_setup(teardown=reset_config)
def ed_visualization():
    try:
        import matplotlib
    except ImportError:
        raise nose.SkipTest("visualizations require matplotlib")

    run_case("ed", visualization=True)


@istest
@with_setup(teardown=reset_config)
def opf_visualization():
    try:
        import matplotlib
    except ImportError:
        raise nose.SkipTest("visualizations require matplotlib")

    run_case("opf", visualization=True)


@istest
@with_setup(teardown=reset_config)
def uc_visualization():
    try:
        import matplotlib
    except ImportError:
        raise nose.SkipTest("visualizations require matplotlib")

    duals = user_config.solver != "glpk"

    run_case("uc-rolling", visualization=True, duals=duals)
