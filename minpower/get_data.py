"""
Get data from spreadsheet files and parse it into 
:class:`~powersystems.Generator`, :class:`~powersystems.Load`,
:class:`~powersystems.Bus`, and :class:`~powersystems.Line` objects.
Also extract the time information and create a :class:`~schedule.Timelist`
object.
"""

import powersystems
from schedule import *
from commonscripts import *
from stochastic import construct_simple_scenario_tree
from powersystems import PowerSystem
from config import user_config

import os,sys,logging

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
    'noloadcost':'noloadcost', #for a bid points defined gen, this replaces the constant polynomial in the cost coefficient
    'costcurveequation':'costcurvestring','cost':'costcurvestring',
    'heatrateequation':'heatratestring',
    'fuelcost':'fuelcost',
    'startupcost':'startupcost','shutdowncost':'shutdowncost',
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
            'p':'P','pd':'P', 'power':'P',
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

def _has_valid_attr(obj, name):
    return getattr(obj, name, None) is not None

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
    loads = build_class_list(loads_data, powersystems.makeLoad)
    #add generators
    generators = build_class_list(generators_data, powersystems.makeGenerator)
    #add lines
    lines = build_class_list(lines_data, powersystems.Line)    
    
    # remove times not in stage
    for obj in filter(lambda obj: _has_valid_attr(obj, 'schedule'), loads+generators):
        obj.schedule = obj.schedule[times.strings.index]
        obj.schedule.index = times.strings.values
    
    #setup scenario tree (if applicable)
    if user_config.deterministic_solve: 
        scenario_tree = None
    else: 
        scenario_tree = setup_scenarios(generators, times)
    
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

    :param datadir:      directory of data
    :param file_gens:    spreadsheet of generator data
    :param file_loads:   spreadsheet of load data
    :param file_lines:   spreadsheet of line data (not required for ED,UC problems)
    :param file_init:    spreadsheet of initial time generator data
        (not required for ED,OPF problems. Defaults will be used
        for UC problems if not specified.)
    
    :return generators:, list of :class:`~powersystems.Generator` objects 
    :return loads:, list of :class:`~Load` objects
    :return lines:, list of :class:`~powersystems.Line` objects
    :return times:, list of :class:`~schedule.Timelist` object
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
    loads = build_class_list(loads_data, powersystems.makeLoad, timeseries)
    #add generators
    generators = build_class_list(generators_data, powersystems.makeGenerator, timeseries)
    #add lines
    lines = build_class_list(lines_data, powersystems.Line)    
    #add initial conditions
    
    setup_initialcond(init_data, generators, times)
    
    #setup scenario tree (if applicable)
    if user_config.deterministic_solve: 
        scenario_tree = None
    else: 
        scenario_tree = setup_scenarios(generators, times)
    
    return generators,loads,lines,times,scenario_tree

def setup_initialcond(data,generators,times):
    '''
    Take a list of initial conditions parameters and
    add information to each :class:`~powersystems.Generator` 
    object.
    '''
    if len(times)<=1: return generators #for UC,ED no need to set initial status
    
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
    return generators

def build_class_list(data, model, timeseries=None):
    """
    Create list of class instances from data in a spreadsheet.
    
    :param data: a list of dictionaries describing the parameters
    :param model: the :mod:`powersystems` class to map the data to
    :param datadir: the directory where the data (and schedule files are)
    :param times: for :mod:`powersystems` classes which have schedule file information,
        a master:class:`~schedule.Timelist` list to pass to :class:`~schedule.Schedule`
    
    :returns: a list of class objects
    """
    datadir = user_config.directory
    
    all_models=[]
    index=0
    for row in data:      
        row_model = model
        sched_col = row.pop('schedulename',None)
        observed_col = row.pop('observedname', None)
        forecast_col = row.pop('forecastname',None)
        
        
        schedulefilename = row.pop('schedulefilename',None)        
        scenariosfilename = row.pop('scenariosfilename',None)
        scenariosdirectory=row.pop('scenariosdirectory',None)
        bid_points_filename = row.pop('costcurvepointsfilename', None)
        
        if sched_col is not None: 
            row['schedule'] = timeseries[sched_col]
        elif schedulefilename is not None:
            row['schedule'] = get_schedule(joindir(datadir, schedulefilename))
        elif (scenariosfilename is not None) or (scenariosdirectory is not None):
            row_model = powersystems.Generator_Stochastic
        
        
        if user_config.deterministic_solve and forecast_filename is not None: 
            row_model = powersystems.Generator_nonControllable
            row['schedule'] = timeseries[forecast_col]
        
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
        
        if user_config.deterministic_solve and observedfilename is not None:
            obj.observed_values = timeseries[observed_col]
        elif scenariosfilename is not None:
            obj.scenarios_filename  = joindir(datadir,scenariosfilename)
        elif scenariosdirectory is not None: 
            obj.scenarios_directory = joindir(datadir, scenariosdirectory)
            try: obj.observed_values = timeseries[observed_col]
            except: 
                raise AttributeError('you must provide a observed filename for a rolling stochastic UC')

        all_models.append( obj )
        index+=1
    return all_models

def setup_times(generators_data, loads_data, filename_timeseries):
    """ 
    Create list of :class:`~schedule.Time` objects 
    from the schedule files. If there are no schedule
    files (as in ED,OPF), create just a single
    :class:`~schedule.Time` instance.
    
    :param generators_data: list of dictionaries each describing a generator
    :param loads_data:   list of dictionaries each describing a load
    :param datadir:      the directory containing the data
    
    :returns: a :class:`~schedule.Timelist` object
    """
    try: 
        timeseries = ts_from_csv(filename_timeseries, is_df=True)
        if timeseries.index[1] - timeseries.index[0] == datetime.timedelta(0,3600):
            timeseries = timeseries.asfreq('1h')
        
        times = schedule.TimeIndex(timeseries.index)
        
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

def setup_scenarios(generators, times, Nscenarios = user_config.scenarios):
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
        data=csv2dicts(gen.scenarios_filename)
        if Nscenarios is not None:
            data = data[:Nscenarios]
        
        probabilities=[row['probability'] for row in data]
        if Nscenarios is not None:
            pr = sum(probabilities)
            probabilities=[ p/pr for p in probabilities ]
        
        for row in data:
            row.pop('probability')
            gen.scenario_values.append(dict( (times[t],row[time]) for t,time in enumerate(sorted(row.iterkeys())) ))
        return construct_simple_scenario_tree( probabilities )
    elif getattr(gen, 'scenarios_directory', None) is not None: # directory of scenarios grouped by days
        # key scenarios by day (initialization)
        scenario_trees = OrderedDict()
        gen.scenario_values = OrderedDict()
        gen.has_scenarios_multistage = True
        
        # already did this above 
        # load in the observations (needed to decide the final states of each stage)
        # gen.observed_values = dataframe_from_csv(gen.observed_filename, parse_dates=True, index_col=0, squeeze=True)
        # TODO - check for same frequency 
        filenames = sorted(glob(joindir(gen.scenarios_directory, "*.csv")))
        if not filenames: raise IOError('no scenario files in "{}"'.format(gen.scenarios_directory))
        
        for i,f in enumerate(filenames):
            logging.debug('reading scenarios from %s', f)
            data = dataframe_from_csv(f, parse_dates=True, index_col=0)
            
            if Nscenarios is not None:
                data = data[ data.index<Nscenarios ]
                data['probability'] = data['probability']/sum( data['probability'] )
            
            # data_times = date_range(data.columns[1], data.columns[-1],freq='5min')
            day = parse_time(data.columns[1]) #first col is probability
            
            gen.scenario_values[day] = data
            # defer construction until actual time stage starts
            # scenario_trees[day] = construct_simple_scenario_tree( data['probability'].values.tolist(), time_stage=i )
        return scenario_trees
