"""
Get data from spreadsheet files and parse it into 
:class:`~powersystems.Generator`, :class:`~powersystems.Load`,
:class:`~powersystems.Bus`, and :class:`~powersystems.Line` objects.
Also extract the time information and create a :class:`~schedule.Timelist`
object.
"""

import powersystems
import schedule
from addons import *
from commonscripts import *
from stochastic import construct_simple_scenario_tree

import os,sys,logging

fields_lines={'name':'name','to':'To','from':'From','reactance':'X','pmax':'Pmax'}
fields_gens={
    'name':'name','type':'kind','kind':'kind','bus':'bus',
    'pmin':'Pmin','pmax':'Pmax','powermin':'Pmin','powermax':'Pmax',
    'p':'power','pg':'power','power':'power', #for a non-controllable gen in an ED
    'rampratemin':'rampratemin','rampratemax':'rampratemax',
    'minuptime':'minuptime','uptimemin':'minuptime',
    'mindowntime':'mindowntime','downtimemin':'mindowntime',
    'costcurvepointsfilename':'costcurvepointsfilename',
    'noloadcost':'noloadcost', #for a bid points defined gen, this replaces the constant polynomial in the cost coefficient
    'costcurveequation':'costcurvestring','cost':'costcurvestring',
    'heatrateequation':'heatratestring','fuelcost':'fuelcost',
    'startupcost':'startupcost','shutdowncost':'shutdowncost',
    'schedulefilename':'schedulefilename','mustrun':'mustrun',
    'scenariosfilename':'scenariosfilename',
    'scenariosdirectory':'scenariosdirectory',
    'observedfilename':'observedfilename'}
    
fields_loads={'name':'name','bus':'bus','type':'kind','kind':'kind',
            'p':'P','pd':'P', 'power':'P',
            'pmin':'Pmin','pmax':'Pmax',
            'schedulefilename':'schedulefilename','model':'model',
            'bidequation':'costcurvestring','costcurveequation':'costcurvestring'}
fields_initial={
    'name':'name','generatorname':'name',
    'status':'u','u':'u',
    'p':'P','pg':'P','power':'P',
    'hoursinstatus':'hoursinstatus',
    'ic':None}
    
def parsedir(datadir='.',
        Nscenarios = None,
        file_gens='generators.csv',
        file_loads='loads.csv',
        file_lines='lines.csv',
        file_init='initial.csv'):
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
    if not os.path.isdir(datadir): raise OSError('data directory "{d}" does not exist'.format(d=datadir) )
    [file_gens,file_loads,file_lines,file_init]=[joindir(datadir,filename) for filename in (file_gens,file_loads,file_lines,file_init)]
    
    generators_data=csv2dicts(file_gens,field_map=fields_gens)
    loads_data=csv2dicts(file_loads,field_map=fields_loads)
    try: lines_data=csv2dicts(file_lines,field_map=fields_lines)
    except IOError: lines_data=[]
    try: init_data=csv2dicts(file_init,field_map=fields_initial)
    except IOError: init_data=[]
    
    
    #create times
    times=setup_times(generators_data,loads_data,datadir)
    #add loads
    loads=build_class_list(loads_data,powersystems.makeLoad,datadir,times=times)
    #add generators
    generators=build_class_list(generators_data,powersystems.makeGenerator,datadir,times=times)
    #add lines
    lines=build_class_list(lines_data,powersystems.Line,datadir)    
    #add initial conditions
    setup_initialcond(init_data,generators,times)
    
    #setup scenario tree (if applicable)
    scenario_tree=setup_scenarios(generators,times, Nscenarios)
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

def build_class_list(data,model,datadir,times=None,model_schedule=schedule.make_schedule):
    """
    Create list of class instances from data in a spreadsheet.
    
    :param data: a list of dictionaries describing the parameters
    :param model: the :mod:`powersystems` class to map the data to
    :param datadir: the directory where the data (and schedule files are)
    :param times: for :mod:`powersystems` classes which have schedule file information,
        a master:class:`~schedule.Timelist` list to pass to :class:`~schedule.Schedule`
    
    :returns: a list of class objects
    """

    
    def get_model(inputs,default=model,field='model'):
        model=default
        newmodel=inputs.pop(field,None)
        if newmodel is None: return model,model_schedule
        else:
            modname,classname=newmodel.split('.')
            if 'Shifting' in classname: 
                model_schedule_row=getattr(globals()[modname],'make_shifting_schedule')
            else: 
                model_schedule_row=model_schedule
            return getattr(globals()[modname],classname),model_schedule_row
    
    all_models=[]
    index=0
    for row in data:
        model_row,model_schedule_row=get_model(row)
        schedulefilename=row.pop('schedulefilename',None)
        scenariosfilename=row.pop('scenariosfilename',None)
        scenariosdirectory=row.pop('scenariosdirectory',None)
        observedfilename = row.pop('observedfilename', None)
        bid_points_filename = row.pop('costcurvepointsfilename', None)
        
        if schedulefilename is not None: row['schedule']=model_schedule_row(joindir(datadir,schedulefilename),times)
        elif (scenariosfilename is not None) or (scenariosdirectory is not None): model_row = powersystems.Generator_Stochastic
        
        # load a custom bid points filename with {power, cost} columns 
        if bid_points_filename is not None: 
            bid_points = csv2dicts( joindir(datadir, bid_points_filename) ) 
            row['bid_points'] = [ (bp['power'], bp['cost']) for bp in bid_points]
            row['costcurvestring'] = None
            
        
        try: obj=model_row(index=index, **row)
        except TypeError:
            msg='{} model got unexpected parameter'.format(model_row)
            print msg
            raise
        if scenariosfilename is not None:    obj.scenarios_filename  = joindir(datadir,scenariosfilename)
        elif scenariosdirectory is not None: 
            obj.scenarios_directory = joindir(datadir, scenariosdirectory)
            obj.observed_filename = joindir(datadir, observedfilename)
        all_models.append( obj )
        index+=1
    return all_models

def setup_times(generators_data,loads_data,datadir):
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

    time_strings=[]
    schedule_filenames=[]
    
    field_sched='schedulefilename'
    def valid_sched_file(D): return D.get(field_sched,None) is not None and not D.get('model','').count('Shifting')
    schedule_filenames.extend([load[field_sched] for load in loads_data if valid_sched_file(load)])
    schedule_filenames.extend([gen[field_sched] for gen in generators_data if valid_sched_file(gen)])
    
    
    if len(schedule_filenames)==0:
        #this is a ED or OPF problem - only one time
        return schedule.just_one_time()

    for filename in schedule_filenames:
        try: time_strings.append( csvColumn(joindir(datadir,filename),'time') )
        except ValueError:
            time_strings.append( csvColumn(joindir(datadir,filename),'times') )
            
    
    nT =[len(L) for L in time_strings]
    if not all(nT[0]==N for N in nT):
        msg='there is a schedule with inconsistent times. schedule lengths={L}.'.format(L=dict(zip(schedule_filenames,nT)))
        raise ValueError(msg)
    
    
    time_strings=flatten(time_strings)
    time_dates=schedule.parse_timestrings(time_strings)
    
    if not len(time_strings) == max(nT): 
        #need to get a unique list
        time_dates=sorted(unique(time_dates))
    return schedule.make_times(time_dates)

def setup_scenarios(generators,times, Nscenarios = None):
    # no_scenario_indexes=[]
    # FIXME - need to think about how rolling will work here
    
    has_scenarios=[]
    for gen in generators:
        if (getattr(gen,'scenarios_filename',None) is not None) or (getattr(gen, 'scenarios_directory', None) is not None): 
            has_scenarios.append(gen.index)
    
    if len(has_scenarios)>1:
        raise NotImplementedError('more than one generator with scenarios. have not coded this case yet.')
    elif len(has_scenarios)==0: #deterministic model
        return None
        
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
        import pandas
        from pandas.io.parsers import read_csv as dataframe_from_csv
        from collections import OrderedDict
        
        scenario_trees = OrderedDict()
        gen.scenario_values = OrderedDict()
        gen.has_scenarios_multistage = True
        
        # load in the observations (needed to decide the final states of each stage)
        gen.observed_values = dataframe_from_csv(gen.observed_filename, parse_dates=True, index_col=0, squeeze=True)
        
        for root, dirs, files in os.walk(gen.scenarios_directory):
            for i,f in enumerate(sorted(files)):
                data = dataframe_from_csv(joindir(root,f), parse_dates=True, index_col=0)
                
                if Nscenarios is not None:
                    data = data[ data.index<Nscenarios ]
                    data['probability'] = data['probability']/sum( data['probability'] )
                
                # data_times = pandas.date_range(data.columns[1], data.columns[-1],freq='5min')
                day = parse_time(data.columns[1]) #first col is probability
                
                gen.scenario_values[day] = data
                # defer construction until actual time stage starts
                # scenario_trees[day] = construct_simple_scenario_tree( data['probability'].values.tolist(), time_stage=i )
        return scenario_trees
