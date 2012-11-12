from commonscripts import *
from config import user_config

from schedule import TimeIndex
from get_data import parse_standalone

filename = 'stage-store.hd5'

def wipe_storage():
    print 'wipe storage'
    os.remove(joindir(user_config.directory, filename))

def get_storage(): 
    return pd.HDFStore(joindir(user_config.directory, filename))

        
def store_times(tstage, storage=None):
    if storage is None:
        storage = get_storage()
    storage['times'] = tstage.strings        
    return storage
        
def store_state(power_system, times, sln=None):
    storage = get_storage()
    generators = power_system.generators()
   
    if sln is None: 
        # pre-first stage
        stages = len(times) #stage_times
        times = [times[0].initialTime]
        
        storage['power'] = gen_time_dataframe(generators, times, 
            values = [gen.initial_power for gen in generators])        
        storage['status'] = gen_time_dataframe(generators, times, 
            values = [gen.initial_status for gen in generators])
        storage['load_shed'] = Series( [0], index=times)

        storage['hrsinstatus'] = gen_time_dataframe(generators, times, 
            values = [gen.initial_status_hours for gen in generators])
        
        
        
        # per-stage results 
        storage['expected_cost'] = Series(index=range(stages))
        storage['observed_cost'] = Series(index=range(stages))
        storage['solve_time'] = Series(index=range(stages))
        
        # store configuration
        storage['configuration'] = Series(user_config)
        print 'store init config'
        
    else:
        stg = sln.stage_number
        storage['power'] = storage['power'].append(sln.generators_power)
        storage['status'] = storage['status'].append(sln.generators_status)
        storage['load_shed'] = storage['load_shed'].append(sln.load_shed_timeseries)
        
        tEnd = times.last_non_overlap()
        storage['hrsinstatus'] = gen_time_dataframe(generators, [tEnd], 
            values = [gen.finalstatus['hoursinstatus'] for gen in generators])
        
        _add_stage_val(storage, 'expected_cost', stg, sln.objective)
        _add_stage_val(storage, 'solve_time', stg, sln.solve_time)                
        
        if sln.is_stochastic or user_config.deterministic_solve:
            _add_stage_val(storage, 'observed_cost', stg, sln.totalcost_generation)                
                
    return storage
    
def load_state():
    storage = get_storage()
    user_config = storage['configuration'].to_dict()
    
    startidx = int(storage['times'][0].strip('t'))
    times = TimeIndex(storage['times'].index, startidx)

    # create power_system
    power_system, times, scenario_tree = parse_standalone(times)
    generators = power_system.generators()
    
    # set up initial state
    t = times.initialTime
    
    
    for gen in generators: 
        g = str(gen)
        try: gen.set_initial_condition(t, 
            P=storage['power'][g][t],
            u=storage['status'][g][t],
            hoursinstatus=storage['hrsinstatus'][g][t])
        except: set_trace()
    
    return power_system, times, scenario_tree
    
def _add_stage_val(storage, tablename, index, value):
    tbl = storage[tablename]
    tbl[index] = value
    storage[tablename] = tbl
