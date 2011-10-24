"""
Get data from csv files and parse it into lists of power systems class instances
(:class:`~powersystems.Generator`, :class:`~powersystems.Line`, and :class:`~powersystems.Load`). 
Create lists of :class:`~powersystems.Bus` and :class:`~powersystems.Line` instances
from the information found in the data.
"""

import powersystems
import schedule
from addons import *
from commonscripts import readCSV,csvColumn,flatten,unique,drop_case_spaces,joindir

import os,sys,logging

fields_lines={'name':'name','to':'To','from':'From','pmax':'Pmax'}
fields_gens={
    'name':'name','type':'kind','kind':'kind','bus':'bus',
    'pmin':'Pmin','pmax':'Pmax',
    'p':'power','pg':'power','power':'power', #for a non-controllable gen in an ED
    'rampratemin':'rampratemin','rampratemax':'rampratemax',
    'minuptime':'minuptime','mindowntime':'mindowntime',
    'costcurveequation':'costcurvestring', 
    'heatrateequation':'heatratestring','fuelcost':'fuelcost',
    'startupcost':'startupcost','shutdowncost':'shutdowncost',
    'schedulefilename':'schedulefilename','mustrun':'mustrun'}
fields_loads={'name':'name','bus':'bus','type':'kind','kind':'kind',
            'p':'P','pd':'P', 'power':'P',
            'pmin':'Pmin','pmax':'Pmax',
            'schedulefilename':'schedulefilename',
            'bidequation':'costcurvestring','costcurveequation':'costcurvestring'}
fields_initial={
    'name':'name','generatorname':'name',
    'status':'u','u':'u',
    'p':'P','pg':'P','power':'P',
    'hoursinstatus':'hoursinstatus',
    'ic':None}
    
def parsedir(datadir='.',
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
    
    :returns: buses, lines, times (lists of objects)
    """
    if not os.path.isdir(datadir): raise OSError('data directory "{d}" does not exist'.format(d=datadir) )
    [file_gens,file_loads,file_lines,file_init]=[joindir(datadir,filename) for filename in (file_gens,file_loads,file_lines,file_init)]

    #create times
    times=setup_times(file_gens,file_loads,datadir)
    
    #add loads
    loads=build_class_list(file_loads,model=powersystems.makeLoad,field_attr_map=fields_loads,times=times)
    
    #add gens
    generators=build_class_list(file_gens,model=powersystems.makeGenerator,field_attr_map=fields_gens,times=times)
    
    #add initial conditions
    generators=setup_initialcond(file_init,generators,times)
    
    #add lines
    try: lines=build_class_list(file_lines,model=powersystems.Line,field_attr_map=fields_lines)
    except IOError: lines=[]
    
    #create buses list    
    buses=powersystems.make_buses_list(loads,generators)
    
    return buses,lines,times

def setup_initialcond(filename,generators,times):
    '''read initial conditions from spreadsheet and add information to each :class:`powersystems.Generator`.'''
    if len(times)<=1: return generators #for UC,ED no need to set initial status
    validFields=fields_initial.keys()
    
    initialTime = times.initialTime
    
    try: data,fields=readCSV(filename,validFields)
    except IOError: 
        data,fields=[],[]
        logging.warning('No generation initial conditions file found. Setting to defaults.')
        for gen in generators: gen.setInitialCondition(time=initialTime)
        return generators
        
    try: attributes=[fields_initial[drop_case_spaces(f)] for f in fields]
    except KeyError:
        print 'Field "{f}" is not in valid fields (case insensitive): {V}.'.format(f=f,V=validFields)
        raise
    
    
    #set initial condition for all gens to off
    for g in generators: g.setInitialCondition(initialTime, u=False, P=0)


    #overwrite initial condition for generators which are specified in the initial file
    genNames=[g.name for g in generators]
    nameCol = attributes.index('name')
    excludeCols = [nameCol]
    if None in attributes: excludeCols.append( attributes.index(None) )
    for row in data:
        inputs=dict()
        for c,elem in enumerate(row): 
            if c in excludeCols: continue
            elif elem is not None: inputs[attributes[c]]=elem
        g=genNames.index(row[nameCol])
        generators[g].setInitialCondition(time=initialTime,**inputs)
        
    return generators

def build_class_list(filename,model,field_attr_map,times=None):
    """
    Create list of class instances from data in a spreadsheet.
    
    :param filename: the spreadsheet file (currently just .csv)
    :param classname: the :mod:`powersystems` class to map the data to
    :param field_attr_map: the map from field name (the first row of the spreadsheet) to attribute (the class)
    :param times: for :mod:`powersystems` classes which have schedule file information,
        a master:class:`~schedule.Timelist` list to pass to :class:`~schedule.Schedule`
    
    :returns: a list of class objects
    """
    field_attr_map.update({'model':'model','modelschedule':'modelschedule'}) #add a model override
    dirname=os.path.dirname(filename)
    classL=[]
    validFields=field_attr_map.keys()
    data,fields=readCSV(filename,validFields)
    try: attributes=[field_attr_map[drop_case_spaces(f)] for f in fields]
    except KeyError:
        msg='Field "{f}" is not in list of valid fields for {m} (case insensitive): {V}.'.format(f=f,m=model,V=validFields)
        raise KeyError(msg)
    
    def getmodel(default,name,inputs):
        model=default
        newmodel=inputs.pop(name,None)
        if newmodel is None:
            return model
        else:
            modname,classname=newmodel.split('.')
            return getattr(globals()[modname],classname)
    
    
    index=0
    for row in data:
        inputs=dict()
        for c,elem in enumerate(row): 
            if row[c] is None: continue
            else: inputs[attributes[c]]= row[c]
        else:
            model_local         =getmodel(model,'model',inputs)
            model_schedule_local=getmodel(schedule.makeSchedule,'modelschedule',inputs)

            schedulefilename=inputs.pop('schedulefilename',None)
            if schedulefilename is not None:
                inputs['schedule']=model_schedule_local(joindir(dirname,schedulefilename),times)
            
            classL.append( model_local(index=index, **inputs) )
            index+=1
    return classL

def setup_times(file_gens,file_loads,datadir):
    """ Create list of :class:`~schedule.Time` objects 
        from the schedule files. If there are no schedule
        files (as in ED,OPF), create just a single
        :class:`~schedule.Time` instance.
        
        :param file_gens:    spreadsheet of generator data
        :param file_loads:   spreadsheet of load data
        :param datadir:      directory of data
        
        :returns: a :class:`~schedule.Timelist` object
    """


    def getTimeCol(filename):
        if filename is None: return []
        try: return csvColumn(joindir(datadir,filename),'time')
        except ValueError: return [] 


    timestrL_loads=[]
    timestrL_gens=[]
    
    schedField='schedulefilename'
    try: loadScheds=csvColumn(file_loads,schedField)
    except ValueError: loadScheds=[]
    try: genScheds=csvColumn(file_gens,schedField)
    except ValueError: genScheds=[]    
    
    if len(genScheds)==0 and len(loadScheds)==0:
        #this is a ED or OPF problem - only one time
        times=schedule.just_one_time()
        return times


    for filename in loadScheds: timestrL_loads.append( getTimeCol(filename) )
    for filename in genScheds:  timestrL_gens.append( getTimeCol(filename) )
    nT_loads=[len(L) for L in timestrL_loads]
    nT_gens =[len(L) for L in timestrL_gens]
    
    timestrL =flatten(timestrL_loads)+flatten(timestrL_gens)
    timedateL=schedule.parse_timestrings(timestrL)
    
    if len(timestrL) == max(n for n in nT_loads+nT_gens): 
        times=schedule.makeTimes(timedateL) #just one schedule
    else: 
        uniqueTimes=unique(timedateL)
        #make times from unique list
        times=schedule.makeTimes(uniqueTimes)
        
    #check for missing data problems by checking length
    nT=len(times)
    if any(n!=nT if n else False for n in nT_loads): 
        msg='a load has schedule with inconsistent times. load schedule lengths={L} and there are {t} times.'.format(L=nT_loads,t=nT)
        raise ValueError(msg)
    if any(n!=nT if n else False for n in nT_gens): 
        msg='a generator has schedule with inconsistent times. gen schedule lengths={L} and there are {t} times.'.format(L=nT_gens,t=nT)
        raise ValueError(msg)
    return times

if __name__ == "__main__": 
    if len(sys.argv)==1: parsedir()
    else: 
        datadir=sys.argv[1]
        parsedir(datadir=datadir)
