"""
Get data from spreadsheet files and parse it into 
:class:`~Generator`, :class:`~powersystems.Load`,
:class:`~powersystems.Bus`, and :class:`~powersystems.Line` objects.
Also extract the time information and create all
    :class:`~schedule.Timelist` objects.
"""

from pandas import Series, read_csv, Timestamp
from glob import glob
from collections import OrderedDict
import powersystems
from schedule import (just_one_time, datetime, get_schedule, TimeIndex)
from commonscripts import (joindir, csv2dicts, ts_from_csv)
from stochastic import construct_simple_scenario_tree

from powersystems import PowerSystem
from generators import (Generator, 
    Generator_Stochastic, Generator_nonControllable)
from config import user_config


import os, logging

fields_lines={'name':'name','to':'To','from':'From','reactance':'X','pmax':'Pmax'}
fields_gens={
    'name':'name','type':'kind','kind':'kind','bus':'bus',
    'pmin':'Pmin','pmax':'Pmax','powermin':'Pmin','powermax':'Pmax',
    'p':'power','pg':'power','power':'power', #for a non-controllable gen in an ED
    'rampratemin':'rampratemin','rampratemax':'rampratemax',
    'rampmin':'rampratemin','rampmax':'rampratemax',
    'minuptime':'minuptime','uptimemin':'minuptime',
    'mindowntime':'mindowntime','downtimemin':'mindowntime',
    'costcurvepointsfilename':'costcurvepointsfilename',
    #for a bid points defined gen, noloadcost replaces the constant polynomial
    'noloadcost':'noloadcost', 
    'costcurveequation':'costcurvestring','cost':'costcurvestring',
    'heatrateequation':'heatratestring',
    'fuelcost':'fuelcost',
    'startupcost':'startupcost','shutdowncost':'shutdowncost',
    'faststart':'faststart',
    'schedulefilename':'schedulefilename','mustrun':'mustrun',
    'scenariosfilename':'scenariosfilename',
    'scenariosdirectory':'scenariosdirectory',
    # observed filename is the observed wind and will evaluate the cost of a stochastic solution
    'observedfilename':'observedfilename',
     # forecast filename is a deterministic (point) wind forecast and will be evaluated against observed wind
    'forecastfilename':'forecastfilename',
    
    'schedulename':'schedulename',
    'forecastname':'forecastname',
    'observedname':'observedname',
    
    }
    
fields_loads={'name':'name','bus':'bus','type':'kind','kind':'kind',
            'p':'power','pd':'power', 'power':'power',
            'pmin':'Pmin','pmax':'Pmax',
            'schedulefilename':'schedulefilename','model':'model',
            'bidequation':'costcurvestring','costcurveequation':'costcurvestring',
            
            'schedulename':'schedulename',
            }
fields_initial={
    'name':'name','generatorname':'name',
    'status':'u','u':'u',
    'p':'P','pg':'P','power':'P',
    'hoursinstatus':'hoursinstatus',
    'ic':None}

def parse_standalone(
        times,
        file_gens='generators.csv',
        file_loads='loads.csv',
        file_lines='lines.csv'):
    datadir = user_config.directory
    
    if not os.path.isdir(datadir): 
        raise OSError('data directory "{d}" does not exist'.format(d=datadir))
    [file_gens,file_loads,file_lines]=[joindir(datadir,fnm) for fnm in (file_gens,file_loads,file_lines)]
    
    generators_data=csv2dicts(file_gens,field_map=fields_gens)
    loads_data=csv2dicts(file_loads,field_map=fields_loads)
    try: lines_data=csv2dicts(file_lines,field_map=fields_lines)
    except IOError: lines_data=[]
    
    #add loads
    loads = build_class_list(loads_data, powersystems.Load)
    #add generators
    generators = build_class_list(generators_data, Generator)
    #add lines
    lines = build_class_list(lines_data, powersystems.Line)    
        
    # remove times not in stage
    for obj in filter(lambda obj: _has_valid_attr(obj, 'schedule'), loads+generators):
        obj.schedule = obj.schedule[times.strings.index]
        obj.schedule.index = times.strings.values

    for obj in filter(lambda obj: _has_valid_attr(obj, 'observed_values'), generators):
        obj.observed_values = obj.observed_values[times.strings.index]
        obj.observed_values.index = times.strings.values
        
    #setup scenario tree (if applicable)
    if user_config.deterministic_solve or user_config.perfect_solve: 
        scenario_tree = None
    else: 
        scenario_tree = setup_scenarios(generators, times, only_stage=True)
    
    power_system = PowerSystem(generators,loads,lines)
    
    return power_system,times,scenario_tree

    
def parsedir(
        file_gens='generators.csv',
        file_loads='loads.csv',
        file_lines='lines.csv',
        file_init='initial.csv',
        file_timeseries='timeseries.csv'
        ):
    """
    Import data from spreadsheets and build lists of
    :mod:`powersystems` classes.
    """
    
    datadir = user_config.directory
    
    if not os.path.isdir(datadir): raise OSError('data directory "{d}" does not exist'.format(d=datadir) )
    [file_gens,file_loads,file_lines,file_init, file_timeseries]=[joindir(datadir,filename) for filename in (file_gens,file_loads,file_lines,file_init, file_timeseries)]
    
    
    
    generators_data=csv2dicts(file_gens,field_map=fields_gens)
    loads_data=csv2dicts(file_loads,field_map=fields_loads)
    try: lines_data=csv2dicts(file_lines,field_map=fields_lines)
    except IOError: lines_data=[]
    try: init_data=csv2dicts(file_init,field_map=fields_initial)
    except IOError: init_data=[]
    
    #create times
    timeseries, times = setup_times(generators_data, loads_data, file_timeseries)
    #add loads
    loads = build_class_list(loads_data, powersystems.Load, times, timeseries)
    #add generators
    generators = build_class_list(generators_data, Generator, times, timeseries)
    #add lines
    lines = build_class_list(lines_data, powersystems.Line)    
    #add initial conditions    
    setup_initialcond(init_data, generators, times)

    for obj in filter(lambda obj: _has_valid_attr(obj, 'schedule'), loads+generators):
        #reindex the schedules by the strings (like "t05")
        obj.schedule.index = times.strings.values
        

    
    #setup scenario tree (if applicable)
    if user_config.deterministic_solve or user_config.perfect_solve: 
        scenario_tree = None
    else: 
        scenario_tree = setup_scenarios(generators, times)
    
    return generators,loads,lines,times,scenario_tree

def setup_initialcond(data,generators,times):
    '''
    Take a list of initial conditions parameters and
    add information to each :class:`~Generator` object.
    '''
    if len(times)<=1: return #for UC,ED no need to set initial status
    
    t_init = times.initialTime
    if not data:
        logging.warning('No generation initial conditions file found. Setting to defaults.')
        for gen in generators: gen.set_initial_condition(time=t_init)
        return
        
    #begin by setting initial condition for all generators to off
    for g in generators: g.set_initial_condition(t_init, u=False, P=0)

    names=[g.name for g in generators]
    try_in_order= len(data)==len(generators)

    #overwrite initial condition for generators which are specified in the initial file
    for g,row in enumerate(data):
        name=row.pop('name',names[g] if try_in_order else None)
        g=names.index(name)
        generators[g].set_initial_condition(time=t_init,**row)        
    return

def build_class_list(data, model, times=None, timeseries=None):
    """
    Create list of class instances from data in a spreadsheet.
    """
    datadir = user_config.directory
    is_generator = (model == Generator)
    
    all_models=[]
    index=0
    for row in data:      
        row_model = model

        power = row.pop('power', None)
        sched_col = row.pop('schedulename',None)
        schedulefilename = row.pop('schedulefilename',None)

        if is_generator:
            observed_col = row.pop('observedname', None)
            forecast_col = row.pop('forecastname',None)
                        
            observedfilename = row.pop('observedfilename',None)
            forecastfilename = row.pop('forecastfilename',None)

            scenariosfilename = row.pop('scenariosfilename',None)
            scenariosdirectory = row.pop('scenariosdirectory',None)
            
            if scenariosdirectory and user_config.scenarios_directory:
                scenariosdirectory = user_config.scenarios_directory
            
            bid_points_filename = row.pop('costcurvepointsfilename', None)

        
        if power is not None: 
            # a fixed power for all times
            row['schedule'] = Series(power, times.strings.index)
        elif (sched_col is not None) or (schedulefilename is not None):
            row['schedule'] = _tsorfile(schedulefilename, datadir, timeseries, sched_col)  
        elif is_generator and ((scenariosdirectory is not None) or (scenariosfilename is not None)):
            row_model = Generator_Stochastic
        
        if is_generator:
            if row.get('schedule') is not None:
                row_model = Generator_nonControllable

            if user_config.deterministic_solve and (forecastfilename is not None): 
                row_model = Generator_nonControllable
                row['schedule'] = _tsorfile(forecastfilename, datadir, timeseries, forecast_col)
            elif user_config.perfect_solve and (observedfilename is not None):
                # for a perfect information solve forecast = observed
                row['schedule'] = _tsorfile(observedfilename, datadir, timeseries, observed_col)
                
                # load a custom bid points filename with {power, cost} columns 
            if bid_points_filename is not None: 
                bid_points = csv2dicts( joindir(datadir, bid_points_filename) ) 
                row['bid_points'] = [ (bp['power'], bp['cost']) for bp in bid_points]
                row['costcurvestring'] = None
        
        try: obj=row_model(index=index, **row)
        except TypeError:
            msg='{} model got unexpected parameter'.format(model)
            print msg
            raise

        if is_generator:
            if observedfilename and (user_config.deterministic_solve or user_config.perfect_solve):
                obj.observed_values = _tsorfile(observedfilename, datadir, timeseries, observed_col)
            elif scenariosdirectory is not None: 
                obj.scenarios_directory = joindir(datadir, scenariosdirectory)
                try:
                    obj.observed_values = _tsorfile(observedfilename, datadir, timeseries, observed_col)
                except:
                    raise IOError('you must provide a observed filename for a rolling stochastic UC')
            elif scenariosfilename is not None:
                obj.scenarios_filename = scenariosfilename
                    

        all_models.append( obj )
        index+=1
    return all_models

def _tsorfile(filename, datadir, timeseries, col):
    if timeseries is not None:
        sched = timeseries[col]
    else:
        sched = get_schedule(joindir(datadir, filename))
    return sched
    
    

def setup_times(generators_data, loads_data, filename_timeseries):
    """ 
    Create a :class:`~schedule.TimeIndex` object
    from the schedule files. If there are no schedule
    files (as in ED,OPF), create an index with just a single time.
    """
    try: 
        timeseries = ts_from_csv(filename_timeseries, is_df=True)
        if timeseries.index[1] - timeseries.index[0] == datetime.timedelta(0,3600):
            timeseries = timeseries.asfreq('1h')
        
        times = TimeIndex(timeseries.index)
        
        return timeseries, times
    except IOError:
        pass
        # the old way...
    
    field_sched = 'schedulefilename'

    valid_sched = lambda obj: obj.get(field_sched, None) is not None
    
    scheduled_components = filter(valid_sched, loads_data+generators_data)
    
    if len(scheduled_components)==0:
        #this is a ED or OPF problem - only one time
        return None, just_one_time()
    
    datadir = user_config.directory
    for obj in scheduled_components:
        fnm = obj.pop(field_sched)
        obj['schedule'] = get_schedule(joindir(datadir,fnm) )
    
    lengths = [len(obj['schedule']) for obj in scheduled_components]
    if not all(ln==lengths[0] for ln in lengths):
        raise ValueError('not all schedules the same length')
    
    times = TimeIndex(scheduled_components[0]['schedule'].index)

    for obj in scheduled_components:
        obj['schedule'].index = times.strings.values

    return None, times

def _parse_scenario_day(filename):
    logging.debug('reading scenarios from %s', filename)
    data = read_csv(filename, parse_dates=True, index_col=0)
    Nscenarios = user_config.scenarios
    
    if Nscenarios is not None:
        data = data[ data.index<Nscenarios ]
        data['probability'] = data['probability']/sum( data['probability'] )
        
    return data  

def setup_scenarios(generators, times, only_stage=False):
    if user_config.deterministic_solve: return None
    
    has_scenarios=[]
    for gen in generators:
        if (getattr(gen,'scenarios_filename',None) is not None) or (getattr(gen, 'scenarios_directory', None) is not None): 
            has_scenarios.append(gen.index)
            
    if len(has_scenarios)==0: #deterministic model
        return None
    elif len(has_scenarios)>1:
        raise NotImplementedError('more than one generator with scenarios. have not coded this case yet.')
        
    #select the one gen with scenarios
    gen=generators[has_scenarios[0]]
    gen.has_scenarios=True
    gen.scenario_values=[]
    
    if getattr(gen,'scenarios_filename',None) is not None:
        
        gen.has_scenarios_multistage = False
        fnm = joindir(user_config.directory, gen.scenarios_filename)
        gen.scenario_values = read_csv(fnm)
        
        probabilities = gen.scenario_values['probability'].values.tolist()
        
        return construct_simple_scenario_tree( probabilities )
        
    elif getattr(gen, 'scenarios_directory', None) is not None: # directory of scenarios grouped by days
        # key scenarios by day (initialization)
        scenario_trees = OrderedDict()
        gen.scenario_values = OrderedDict()
        
        gen.has_scenarios_multistage = True        
        if only_stage:
            stage_date = times.strings.index[0].date()
            searchstr = "*{}.csv".format(stage_date)
        else: 
            searchstr = "*.csv"
        
        filenames = sorted(glob(joindir(gen.scenarios_directory, searchstr)))
        if not filenames: raise IOError('no scenario files in "{}"'.format(gen.scenarios_directory))
        
        for i,f in enumerate(filenames):
            data = _parse_scenario_day(f)
            day_idx = 1 if data.columns[0]=='probability' else 0
            day = Timestamp(data.columns[day_idx]).date() 
            gen.scenario_values[day] = data
        
        # defer construction until actual time stage starts
        return scenario_trees

def _has_valid_attr(obj, name):
    return getattr(obj, name, None) is not None
