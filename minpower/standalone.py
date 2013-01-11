"""
A module to workaround a memory leak in coopr by saving the results 
of each day of a rolling unit commitment to disk (in HDF format)
and reloading them to run the next day as a memory independent subprocess.
"""

import os, logging, sys
import pandas as pd
from pandas import Series, DataFrame
from commonscripts import gen_time_dataframe, set_trace
from config import user_config

from schedule import TimeIndex
from get_data import parse_standalone
import pkg_resources

def wipe_storage():
    try: 
        os.remove(user_config.store_filename)
        print 'wipe storage'
    except OSError: pass
    

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
        key = 'data_' + key
        storage[key] = df
    
    stages = len(times) #stage_times
    t = [times[0].initialTime]
    
    # store first stage initial state
    storage['power'] = gen_time_dataframe(generators, t, 
        values = [[gen.initial_power for gen in generators]])
    storage['status'] = gen_time_dataframe(generators, t, 
        values = [[gen.initial_status for gen in generators]])
    storage['hrsinstatus'] = gen_time_dataframe(generators, t, 
        values = [[gen.initial_status_hours for gen in generators]])

    # setup empty containers for variables
    storage['load_shed'] = Series()
    storage['expected_cost'] = DataFrame()
    storage['observed_cost'] = DataFrame()
    storage['expected_status'] = DataFrame()
    storage['expected_power'] = DataFrame()
    
    # setup one-per-stage results
    storage['solve_time'] = Series(index=range(stages))
    storage['mipgap'] = Series(index=range(stages))
    
    # store configuration
    storage['configuration'] = Series(user_config)
    
    
    storage['version'] = Series({'minpower': 
        pkg_resources.get_distribution('minpower').version})
    return storage
    
def store_state(power_system, times, sln=None):
    storage = get_storage()
    generators = power_system.generators()
   
    stg = sln.stage_number
    table_append(storage, 'power', sln.generators_power)
    table_append(storage, 'status', sln.generators_status)
    table_append(storage, 'load_shed', sln.load_shed_timeseries)
    
    tEnd = times.last_non_overlap()
    storage['hrsinstatus'] = gen_time_dataframe(generators, [tEnd], 
        values = [
            [gen.finalstatus['hoursinstatus'] for gen in generators]
        ])
    
    _add_tbl_val(storage, 'solve_time', stg, sln.solve_time)
    _add_tbl_val(storage, 'mipgap', stg, sln.mipgap)
    
    if sln.is_stochastic or user_config.deterministic_solve:
        table_append(storage, 'observed_cost', sln.observed_totalcost)
        table_append(storage, 'expected_cost', sln.expected_totalcost)
        table_append(storage, 'expected_power', sln.expected_power)
        table_append(storage, 'expected_status', sln.expected_status)
    else:
        table_append(storage, 'expected_cost', sln.totalcost_generation)
    return storage
    
def load_state():
    storage = get_storage()
    user_config.update(storage['configuration'].to_dict())
    
    # set up the times
    startidx = int(storage['times'][0].strip('t'))
    times = TimeIndex(storage['times'].index, startidx)
    intervalhrs = (times.strings.index[1] - times.strings.index[0]).total_seconds() / 3600.0
    times._int_overlap = user_config.hours_overlap / intervalhrs
    times._int_division = user_config.hours_commitment / intervalhrs

    # create power_system
    power_system, times, scenario_tree = parse_standalone(storage, times)
    generators = power_system.generators()
    
    # set up initial state
    t = times.initialTime
    
    
    for gen in generators: 
        g = str(gen)
        gen.set_initial_condition(t, 
            power=storage['power'][g][t],
            status=storage['status'][g][t],
            hoursinstatus=storage['hrsinstatus'][g][t])
    
    return power_system, times, scenario_tree

def repack_storage():
    '''compress that ballooning storage'''
    # http://stackoverflow.com/questions/13089359/mystery-when-storing-a-dataframe-containing-strings-in-hdf-with-pandas
    os.system('ptrepack {f} {f}.copy; mv {f}.copy {f};'.format(
        f=user_config.store_filename))
    
def _add_tbl_val(storage, tablename, index, value):
    tbl = storage[tablename]
    tbl[index] = value
    storage[tablename] = tbl
    
def table_append(store, name, newvals):
    store[name] = store[name].append(newvals)
    return
    
try: 
    import tables as tb
    import atexit
    
    # FIXME - not working
    # make pytables quiet down
    # http://www.pytables.org/moin/UserDocuments/AtexitHooks
    def quiet_table_close(verbose=False):
        open_files = tb.file._open_files
        are_open_files = len(open_files) > 0
        if verbose and are_open_files:
            print >> sys.stderr, "Closing remaining open files:",
        for fileh in open_files.keys():
            if verbose:
                print >> sys.stderr, "%s..." % (open_files[fileh].filename,),
            open_files[fileh].close()
            if verbose:
                print >> sys.stderr, "done",
        if verbose and are_open_files:
            print >> sys.stderr

    atexit.register(quiet_table_close)
    
except ImportError:
    logging.debug('could not load pytables - cannot use standalone mode.')
