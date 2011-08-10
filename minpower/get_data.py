"""
Get data from csv files and parse it into lists of power systems class instances
(:class:`~powersystems.Generator`, :class:`~powersystems.Line`, and :class:`~powersystems.Load`). 
Create lists of :class:`~powersystems.Bus` and :class:`~powersystems.Line` instances
from the information found in the data.
"""

import powersystems
import schedule
from commonscripts import readCSV,csvColumn,flatten,unique,drop_case_spaces,getattrL, joindir

import os,sys,logging
import dateutil
import numpy as np

fields_lines={'name':'name','to':'To','from':'From','pmax':'Pmax'}
fields_gens={
    'name':'name','type':'kind','kind':'kind','bus':'bus',
    'pmin':'Pmin','pmax':'Pmax',
    'rampratemin':'rampratemin','rampratemax':'rampratemax',
    'minuptime':'minuptime','mindowntime':'mindowntime',
    'costcurveequation':'costcurvestring', 
    'heatrateequation':'heatratestring','fuelcost':'fuelcost',
    'startupcost':'startupcost','shutdowncost':'shutdowncost',
    'schedulefilename':'schedulefilename','mustrun':'mustrun'}
fields_loads={'name':'name','bus':'bus','type':'kind','kind':'kind',
            'p':'P','pd':'P', 'pmin':'Pmin','pmax':'Pmax',
            'schedulefilename':'schedulefilename',
            'bidequation':'costcurvestring','costcurveequation':'costcurvestring'}

def parsedir(datadir='./tests/uc/',
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
    loads=build_class_list(file_loads,classname=powersystems.makeLoad,field_attr_map=fields_loads,times=times)
    
    #add gens
    generators=build_class_list(file_gens,classname=powersystems.makeGenerator,field_attr_map=fields_gens,times=times)
    
    #add initial conditions
    generators=setup_initialcond(file_init,generators,times)
    
    #add lines
    try: lines=build_class_list(file_lines,classname=powersystems.Line,field_attr_map=fields_lines)
    except IOError: lines=[]
    
    #create buses list    
    buses=setup_buses(loads,generators)
    
    return buses,lines,times

def setup_initialcond(filename,generators,times):
    '''read initial conditions from spreadsheet and add information to each :class:`powersystems.Generator`.'''
    if len(times)<=1: return generators #for UC,ED no need to set initial status
    field_attr_map={'name':'name','status':'u','p':'P','hoursinstatus':'hoursinstatus'}
    validFields=field_attr_map.keys()
    
    initialTime = times.initialTime
    
    try: data,fields=readCSV(filename,validFields)
    except IOError: 
        data,fields=[],[]
        logging.warning('No generation initial conditions file found. Setting to defaults.')
        for gen in generators: gen.setInitialCondition(time=initialTime)
        return generators
        
    try: attributes=[field_attr_map[drop_case_spaces(f)] for f in fields]
    except KeyError:
        print 'Field "{f}" is not in valid fields (case insensitive): {V}.'.format(f=f,V=validFields)
        raise
    
    
    #add info to generators
    genNames=[g.name for g in generators]
    nameCol = attributes.index('name')
    for row in data:
        inputs=dict()
        for c,elem in enumerate(row): 
            if c==nameCol: continue
            elif row[c] is not None: inputs[attributes[c]]=row[c]
        g=genNames.index(row[nameCol])
        generators[g].setInitialCondition(time=initialTime,**inputs)
        
    return generators

def build_class_list(filename,classname,field_attr_map,times=None):
    """
    Create list of class instances from data in a spreadsheet.
    
    :param filename: the spreadsheet file (currently just .csv)
    :param classname: the :mod:`powersystems` class to map the data to
    :param field_attr_map: the map from field name (the first row of the spreadsheet) to attribute (the class)
    :param times: for :mod:`powersystems` classes which have schedule file information,
        a master:class:`~schedule.Timelist` list to pass to :class:`~schedule.Schedule`
    
    :returns: a list of class objects
    """
        
    dirname=os.path.dirname(filename)
    classL=[]
    validFields=field_attr_map.keys()
    data,fields=readCSV(filename,validFields)
    try: attributes=[field_attr_map[drop_case_spaces(f)] for f in fields]
    except KeyError:
        raise KeyError('Field "{f}" is not in list'.format(f=f)+
            'of valid fields (case insensitive): {V}.'.format(V=validFields))
    
    index=0
    for row in data:
        inputs=dict()
        for c,elem in enumerate(row): 
            if row[c] is None: continue
            elif attributes[c]=='schedulefilename':
                schedulefilename=joindir(dirname,row[c])
                inputs['schedule']=schedule.Schedule(schedulefilename,times)
            else: inputs[attributes[c]]= row[c]
        else:
            classL.append( classname(index=index, **inputs) )
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

    def makeTimes(datetimeL):
        '''convert list of datetime objects to Timelist() class'''
        S=datetimeL[0]
        I=datetimeL[1] - S #interval
        E=datetimeL[-1] + I #one past the last time
        times=schedule.Timelist(Start=S,End=E,interval=I)
        times.setInitial()
        return times

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
        times=schedule.Timelist([schedule.Time(Start='0:00',index=0)])
        return times


    for filename in loadScheds: timestrL_loads.append( getTimeCol(filename) )
    for filename in genScheds:  timestrL_gens.append( getTimeCol(filename) )
    nT_loads=[len(L) for L in timestrL_loads]
    nT_gens =[len(L) for L in timestrL_gens]
    
    timestrL =flatten(timestrL_loads)+flatten(timestrL_gens)
    timedateL=schedule.parse_timestrings(timestrL)
    
    if len(timestrL) == max(n for n in nT_loads+nT_gens): 
        times=makeTimes(timedateL) #just one schedule
    else: 
        uniqueTimes=unique(timedateL)
        #make times from unique list
        times=makeTimes(uniqueTimes)
    
    #check for missing data problems by checking length
    nT=len(times)
    if any(n!=nT if n else False for n in nT_loads ): raise ValueError('a load has schedule with inconsistent times. load schedule lengths={L} and there are {t} times.'.format(L=nT_loads,t=nT))
    if any(n!=nT if n else False for n in nT_gens  ): raise ValueError('a generator has schedule with inconsistent times. gen schedule lengths={L} and there are {t} times.'.format(L=nT_gens,t=nT))
    return times
    
    
def setup_buses(loads,generators):
    """Create list of :class:`powersystems.Bus` objects 
        from the load and generator bus names. Otherwise
        (as in ED,UC) create just one (system)
        :class:`powersystems.Bus` instance.
        
        :param loads: a list of :class:`powersystems.Load` objects
        :param generators: a list of :class:`powersystems.Generator` objects
        :returns: a list of :class:`powersystems.Bus` objects
    """
    busNameL=[]
    busNameL.extend(getattrL(generators,'bus'))
    busNameL.extend(getattrL(loads,'bus'))
    busNameL=unique(busNameL)
    buses=[]
    swingHasBeenSet=False
    for b,busNm in enumerate(busNameL):
        newBus=powersystems.Bus(name=busNm,index=b)
        for gen in generators: 
            if gen.bus==newBus.name: newBus.generators.append(gen) 
            if not swingHasBeenSet: newBus.isSwing=swingHasBeenSet=True
        for ld in loads: 
            if ld.bus==newBus.name: newBus.loads.append(ld)             
        buses.append(newBus)
    return buses

if __name__ == "__main__": 
    if len(sys.argv)==1: parsedir()
    else: 
        datadir=sys.argv[1]
        parsedir(datadir=datadir)
