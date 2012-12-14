"""
Get data from spreadsheet files and parse it into 
:class:`~Generator`, :class:`~powersystems.Load`,
:class:`~powersystems.Bus`, and :class:`~powersystems.Line` objects.
Also extract the time information and create all
    :class:`~schedule.Timelist` objects.
"""
import pandas as pd
from pandas import Series, DataFrame, Timestamp, read_csv
from glob import glob
from collections import OrderedDict
import powersystems
from schedule import (just_one_time, datetime, 
    get_schedule, TimeIndex, make_constant_schedule)
from commonscripts import (joindir, drop_case_spaces, ts_from_csv, set_trace)
from stochastic import construct_simple_scenario_tree

from powersystems import PowerSystem
from generators import (Generator, 
    Generator_Stochastic, Generator_nonControllable)
from config import user_config

import os, logging

fields = dict(
    Line=[
    'name',
    'tobus',
    'frombus',
    'reactance',
    'pmax'
    ],

    Generator=[
    'name',
    'kind',
    'bus',
    'pmin', 'pmax',
    'power',  # for a non-controllable gen in an ED
    'rampratemin', 'rampratemax',
    'minuptime', 'mindowntime',
    #for a bid points defined gen, noloadcost replaces the constant polynomial
    'costcurvepointsfilename',
    'noloadcost', 
    'costcurveequation', 'heatrateequation',
    'fuelcost',
    'startupcost', 'shutdowncost',
    'faststart',
    'mustrun', 
    # schedules components
    #'schedulefilename',
    #'scenariosfilename',
    #'scenariosdirectory',
    # observed values (for evaluation of the cost of a stochastic solution)
    #'observedfilename',
    # deterministic (point) forecast vaues
    #'forecastfilename',
    # timeseries in one file names
    #'schedulename', 'forecastname', 'observedname'
    ],

    Load = ['name', 'bus'],
)

fields_initial = [
    'status',
    'power',
    'hoursinstatus']
    
def nice_names(df):
    '''drop the case and spaces from all column names'''
    return df.rename(columns=
        dict([(col, drop_case_spaces(col)) for col in df.columns]))
    
def parse_standalone(storage, times):
    '''load problem info from a pandas.HDFStore'''
    
    # filter timeseries data to only this stage
    timeseries = storage['data_timeseries'].ix[times.strings.values]
    
    #add loads
    loads = build_class_list(storage['data_loads'], powersystems.Load, 
        times, timeseries)
    #add generators
    generators = build_class_list(storage['data_generators'], Generator,
        times, timeseries)
    #add lines
    lines = build_class_list(storage['data_lines'], powersystems.Line,
        times, timeseries)    
            
    #setup scenario tree (if applicable)
    if user_config.deterministic_solve or user_config.perfect_solve: 
        scenario_tree = None
    else: 
        scenario_tree = setup_scenarios(generators, times, only_stage=True)
    
    power_system = PowerSystem(generators, loads, lines)
    
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
    
    if not os.path.isdir(datadir):
        raise OSError('data directory "{d}" does not exist'.format(d=datadir))
    [file_gens, file_loads, file_lines, file_init, file_timeseries] = \
        [joindir(datadir,filename) for filename in 
            (file_gens,file_loads,file_lines,file_init, file_timeseries)]
        
    generators_data = nice_names(read_csv(file_gens))
    loads_data = nice_names(read_csv(file_loads))
    
    try: 
        lines_data = nice_names(read_csv(file_lines))
    except IOError: 
        lines_data = DataFrame()

    try: 
        init_data = nice_names(read_csv(file_init))
    except IOError: 
        init_data = DataFrame()
    
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
    
    #setup scenario tree (if applicable)
    if user_config.deterministic_solve or user_config.perfect_solve: 
        scenario_tree = None
    else: 
        scenario_tree = setup_scenarios(generators, times)
    
    # also return the raw DataFrame objects 
    data = dict(
        generators=generators_data,
        loads=loads_data,
        lines=lines_data,
        init=init_data,
        timeseries=timeseries,
        )
    
    return generators, loads, lines, times, scenario_tree, data


def setup_initialcond(data, generators, times):
    '''
    Take a list of initial conditions parameters and
    add information to each :class:`~Generator` object.
    '''
    if len(times) <= 1: return #for UC,ED no need to set initial status
    
    t_init = times.initialTime
    if len(data) == 0:
        logging.warning('''No generation initial conditions file found. 
            Setting to defaults.''')
        for gen in generators: 
            gen.set_initial_condition(time=t_init)
        return
        
    #begin by setting initial condition for all generators to off
    for g in generators: 
        g.set_initial_condition(t_init, status=False, power=0)

    names = [g.name for g in generators]
    
    if not 'name' in data.columns:
        # assume they are in order
        data['name'] = names
    
    if 'power' not in data.columns: 
        raise KeyError('initial conditions file should contain "power".')
    
    # add initial conditions for generators 
    # which are specified in the initial file
    for i, row in data.iterrows():
        g = names.index(row['name'])
        kwds = row[fields_initial].to_dict()
        generators[g].set_initial_condition(time=t_init, **kwds)
    return


def build_class_list(data, model, times=None, timeseries=None):
    """
    Create list of class instances from the row of a DataFrame.
    """
    datadir = user_config.directory
    is_generator = (model == Generator)
    
    all_models = []
    
    if 'schedulename' in data.columns:
        data['schedule'] = None
    
    for i, row in data.iterrows():
        row_model = model
        row = row.dropna()
        
        power = row.get('power')
        schedulename = row.get('schedulename')
        
        if is_generator:
            # get all those extra things which need to be parsed
            observed_name = row.get('observedname')
            forecast_name = row.get('forecastname')
                        
            scenariosfilename = row.get('scenariosfilename')
            scenariosdirectory = row.get('scenariosdirectory')
            
            if scenariosdirectory and user_config.scenarios_directory:
                # override the scenarios directory with the one \
                # specified in the commandline options
                scenariosdirectory = user_config.scenarios_directory
            
            bid_points_filename = row.get('costcurvepointsfilename')

        
        if is_generator:
            if forecast_name and user_config.deterministic_solve:
                row_model = Generator_nonControllable
            if scenariosdirectory or scenariosfilename:
                row_model = Generator_Stochastic
            elif schedulename:
                row_model = Generator_nonControllable
        
        kwds = row[row.index.isin(fields[model.__name__])].to_dict()
        
        # add in any schedules
        if schedulename:
            kwds['schedule'] = timeseries[schedulename]
        elif pd.notnull(power):
            # a constant power schedule
            kwds['schedule'] = make_constant_schedule(times, power)
            
        if is_generator:
            if observed_name:
                kwds['observed_values'] = timeseries[observed_name]
                            
            if user_config.perfect_solve and observed_name:
                # for a perfect information solve forecast = observed
                kwds['schedule'] = timeseries[observed_name]
            elif forecast_name:
                kwds['schedule'] = timeseries[forecast_name] 
                              
            if scenariosdirectory: 
                kwds['scenarios_directory'] = \
                    joindir(datadir, scenariosdirectory)
                try:
                    kwds['observed_values'] = timeseries[observed_name]
                except:
                    raise IOError('''you must provide an
                        observed filename for a rolling stochastic UC''')
                
            elif scenariosfilename is not None:
                kwds['scenarios_filename'] = scenariosfilename
            
            # add a custom bid points file with {power, cost} columns 
            if bid_points_filename: 
                kwds['bid_points'] = read_bid_points(
                    joindir(datadir, bid_points_filename))
                row.costcurveequation = None
        
        try: 
            obj = row_model(index=i, **kwds)
        except TypeError:
            print '{} model got unexpected parameter'.format(model)
            raise                    

        all_models.append( obj )
        
    return all_models  


def read_bid_points(filename):
    bid_points = read_csv(filename)
    # return a tuple of bidpoints
    return [ (bp['power'], bp['cost']) for bp in bid_points.iterrows()]
    

def setup_times(generators_data, loads_data, filename_timeseries):
    """ 
    Create a :class:`~schedule.TimeIndex` object
    from the schedule files.
    
    Also create a unified DataFrame of all the schedules, `timeseries`.
    
    If there are no schedule files (as in ED,OPF), 
    create an index with just a single time.
    """
    try: 
        timeseries = ts_from_csv(filename_timeseries, is_df=True)
        if timeseries.index[1] - timeseries.index[0] == \
            datetime.timedelta(0, 3600):
            timeseries = timeseries.asfreq('1h')
        
        times = TimeIndex(timeseries.index)
        
        return timeseries, times
    except IOError:
        pass
        # the old way...
    
    fcol = 'schedulefilename'
    ncol = 'schedulename'
            
    loads_data[ncol] = None
    generators_data[ncol] = None
    
    if fcol not in loads_data.columns:
        loads_data[fcol] = None
    if fcol not in generators_data.columns:
        generators_data[fcol] = None
    
    datadir = user_config.directory
    
    timeseries = {}
    
    for i, load in loads_data[loads_data[fcol].notnull()].iterrows():
        name = 'd{}'.format(i)
        loads_data.ix[i, ncol] = name
        timeseries[name] = get_schedule(joindir(datadir, load[fcol]))
    
    for i, gen in generators_data[generators_data[fcol].notnull()].iterrows():
        name = 'g{}'.format(i)
        generators_data.ix[i, ncol] = name
        timeseries[name] = get_schedule(joindir(datadir, gen[fcol]))

    # FIXME - handle observed and forecast power
    #observedfilename = row.pop('observedfilename',None)
    #forecastfilename = row.pop('forecastfilename',None)


    generators_data = generators_data.drop(fcol, axis=1)
    loads_data = loads_data.drop(fcol, axis=1)
        
    if len(timeseries) == 0:
        #this is a ED or OPF problem - only one time
        return DataFrame(), just_one_time()
    
    timeseries = DataFrame(timeseries)        
    times = TimeIndex(timeseries.index)
    timeseries.index = times.strings.values
    return timeseries, times


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
