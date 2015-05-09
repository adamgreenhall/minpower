"""
A module to workaround a memory leak in coopr by saving the results
of each day of a rolling unit commitment to disk (in HDF format)
and reloading them to run the next day as a memory independent subprocess.
"""

import os
import logging
import sys
import pandas as pd
from pandas import Series, DataFrame
from commonscripts import gen_time_dataframe, correct_status, debug_frame_unequal, set_trace
from config import user_config

from schedule import TimeIndex
from get_data import parse_standalone
import pkg_resources


try:
    import tables as tb
except ImportError:
    logging.debug('could not load pytables - cannot use standalone mode.')


def wipe_storage():
    try:
        os.remove(user_config.store_filename)
        logging.debug('wipe storage')
    except OSError:
        pass


def get_storage():
    return pd.HDFStore(user_config.store_filename)


def store_times(tstage, storage=None):
    if storage is None:
        storage = get_storage()
    storage['times'] = tstage.strings
    return storage


def init_store(power_system, times, data):
    '''create the store before the first stage'''
    wipe_storage()
    storage = get_storage()
    generators = power_system.generators()

    # store the problem info read from the spreadsheets
    for key, df in data.iteritems():
        if key != 'scenario_values':
            for k, v in (df.dtypes == object).iterkv():
                if v:
                    df[k] = df[k].fillna('')

        key = 'data_' + key
        storage[key] = df

    stages = len(times)  # stage_times
    est_Nt = len(data['timeseries'])
    t = [times[0].initialTime]

    # store first stage initial state
    storage.append('power',
                   gen_time_dataframe(generators, t,
                                      values=[[gen.initial_power for gen in generators]]),
                   expectedrows=est_Nt)

    storage.append('status',
                   gen_time_dataframe(generators, t,
                                      values=[[gen.initial_status for gen in generators]]),
                   expectedrows=est_Nt)

    storage['hrsinstatus'] = gen_time_dataframe(generators, t,
                                                values=[[gen.initial_status_hours for gen in generators]])

    # setup empty containers for variables
    storage['load_shed'] = Series()
    storage['gen_shed'] = Series()
    storage['expected_cost'] = DataFrame()
    storage['observed_cost'] = DataFrame()
    storage['expected_status'] = DataFrame()
    storage['expected_power'] = DataFrame()
    storage['expected_fuelcost'] = DataFrame()
    storage['observed_fuelcost'] = DataFrame()

    # setup one-per-stage results
    storage['solve_time'] = Series(index=range(stages))
    storage['mipgap'] = Series(index=range(stages))

    # store configuration
    storage['configuration'] = Series(user_config)

    storage['version'] = Series({
        'minpower': pkg_resources.get_distribution('minpower').version,
        # try storing version number of the current working directory
        'problem': _get_problem_version(),
    })

    return storage


def _get_problem_version():
    version = ''
    possible_init = os.path.join(
        os.path.abspath(user_config.directory), '__init__.py')
    if os.path.exists(possible_init):
        vstr = open(possible_init, 'r').read()
        version = vstr.split('"')[1].rstrip('"')
    return version


def store_state(power_system, times, sln=None):
    storage = get_storage()
    generators = power_system.generators()

    stg = sln.stage_number
    table_append(storage, 'power', sln.generators_power)
    table_append(storage, 'status', sln.generators_status)
    table_append(storage, 'load_shed', sln.load_shed_timeseries)
    table_append(storage, 'gen_shed', sln.gen_shed_timeseries)

    tEnd = times.last_non_overlap()
    storage['hrsinstatus'] = gen_time_dataframe(generators, [tEnd],
                                                values=[
                                                [gen.finalstatus['hoursinstatus'] for gen in generators]
                                                ])

    _add_tbl_val(storage, 'solve_time', stg, sln.solve_time)
    _add_tbl_val(storage, 'mipgap', stg, sln.mipgap)

    if sln._resolved:
        table_append(storage, 'observed_cost', sln.observed_totalcost)
        table_append(storage, 'observed_fuelcost', sln.observed_fuelcost)
        table_append(storage, 'expected_cost', sln.expected_totalcost)
        table_append(storage, 'expected_fuelcost', sln.expected_fuelcost)
        table_append(storage, 'expected_power', sln.expected_power)
        table_append(storage, 'expected_status', sln.expected_status)
    else:
        table_append(storage, 'expected_cost', sln.totalcost_generation)
        table_append(storage, 'expected_fuelcost', sln.fuelcost)

#    # DEBUGGING
#    from pandas.util.testing import assert_frame_equal
#    try:
#        gens = storage['data_generators'].copy()
#        gens.index = ['g{}'.format(g) for g in gens.index]
#        status = storage['status'].ix[1:]
#        power = storage['power'][status.columns].ix[status.index]
#        cost = storage['observed_cost'][status.columns].ix[status.index]
#        fuelcost = storage['observed_fuelcost'][status.columns].ix[status.index]
#        stcost = cost - fuelcost

#
#        pcheck = (power * status)
#        ccheck = (cost * status)
#        stcheck = (stcost * status)
#        assert_frame_equal(pcheck, power)
#        assert_frame_equal(ccheck, cost)
#        assert_frame_equal(stcheck, stcost)
#        assert(((stcost < gens.startupcost - 1e-5) & (stcost > 1e-5) ).sum().sum() == 0)
#
#    except AssertionError:
#        raise

    return storage


def load_state():
    storage = get_storage()
    user_config.update(storage['configuration'].to_dict())

    # set up the times
    startidx = int(storage['times'][0].strip('t'))
    times = TimeIndex(storage['times'].index, startidx)
    intervalhrs = (times.strings.index[1] - times.strings.index[0]
                   ).total_seconds() / 3600.0
    times._int_division = user_config.hours_commitment / intervalhrs
    times._int_overlap = user_config.hours_overlap / intervalhrs
    if len(times) <= times._int_division:
        # dont set overlap for last stage
        times._int_overlap = 0

    # create power_system
    power_system, times, scenario_tree = parse_standalone(storage, times)
    generators = power_system.generators()

    # set up initial state
    t = times.initialTime
    status = correct_status(storage['status']).ix[t]
    for gen in generators:
        g = str(gen)
        gen.set_initial_condition(
            power=storage['power'][g][t],
            status=status[g],
            hoursinstatus=storage['hrsinstatus'][g][t])

    return power_system, times, scenario_tree


def repack_storage():
    '''compress that ballooning storage'''
    # http://stackoverflow.com/questions/13089359/mystery-when-storing-a
    # -dataframe-containing-strings-in-hdf-with-pandas
    os.system('ptrepack {f} {f}.copy; mv {f}.copy {f};'.format(
        f=user_config.store_filename))


def _add_tbl_val(storage, tablename, index, value):
    tbl = storage[tablename]
    tbl[index] = value
    storage[tablename] = tbl


def table_append(store, name, newvals):
    store[name] = store[name].append(newvals)
    return
