"""
Defines models for power systems concepts: 
:class:`~powersystems.Bus`, :class:`~powersystems.Generator`, 
:class:`~powersystems.Line`, and :class:`~powersystems.Load`.
"""

from optimization import new_variable,value,sumVars,OptimizationObject
from commonscripts import hours,drop_case_spaces,getattrL,unique,update_attributes
import config, bidding
from schedule import FixedSchedule
import logging

#from dateutil.relativedelta import relativedelta
import numpy 

def makeGenerator(kind='generic',**kwargs):
    """
    Create a :class:`~powersystems.Generator` object 
    (or a :class:`~powersystems.Generator_nonControllable`
    object depending on the kind). First parses defaults
    from :mod:`config`, depending on the kind.
    
    :param kind: define the kind of generator (all 
        kinds are defined in :data:`config.generator_kinds`)
    
    Other parameters are detailed in :class:`~powersystems.Generator`.
    
    :returns: a :class:`~powersystems.Generator` object
    """

    def parse_args(kind,**inputs):
        '''check kind pull defaults from the config file'''
        kind=drop_case_spaces(kind)
        if kind not in config.generator_kinds:
            logging.warning('"k" is an unknown kind of generator, using generic defaults.'.format(k=kind))
            kind='generic'
        
        #get defaults from config file
        defaults=dict()
        for name,val in config.generator_defaults.iteritems():
            try: defaults[name]=val[kind]
            except KeyError:
                logging.debug('no {d} default found for kind "{k}", using default from generic.'.format(d=name,k=kind))
                defaults[name]=val['generic']
            except TypeError: 
                defaults[name]=val #no kind-distincted defaults
                
        #use the values that are defined in the inputs
        outputs=defaults
        outputs.update(inputs)
        return kind,outputs
    
    
    kind,kwargs=parse_args(kind,**kwargs)    
    if kind=='wind' or not kwargs['isControllable'] or kwargs.get('schedule',None) or (kwargs.get('power') is not None): 
        classname=Generator_nonControllable
    else:
        classname=Generator
        kwargs.pop('power')

    kwargs.pop('isControllable')

    return classname(kind=kind,**kwargs)

def makeLoad(kind='varying',**kwargs):
    """
    Create a :class:`~powersystems.Load` object (if a power 
    :class:`~schedule.Schedule` is specified) or a
    :class:`~powersystems.Load_Fixed` object (if a single
    power value :attr:`P` is specified).
    """
    if 'P' in kwargs.keys(): return Load_Fixed(kind=kind, **kwargs)
    else: return Load(kind=kind,**kwargs)
        
class Generator(object):
    """
    A generator model. 
    
    :param Pmin: minimum real power
    :param Pmax: maximum real power
    :param minuptime: min. time after commitment in on status (hours)
    :param mindowntime: min. time after de-commitment in off status (hours)
    :param rampratemax: max. positive change in real power over 1hr (MW/hr)
    :param rampratemin: max. negative change in real power over 1hr (MW/hr)
    :param costcurvestring: text describing a polynomial cost curve ($/MWh)
      see :meth:`~bidding.parsePolynomial` for more.
    :param heatratestring: text describing a polynomial heat rate curve (MBTU/MW). 
        converts to cost curve when multiplied by fuelcost.
    :param fuelcost: cost of fuel ($/MBTU)
    :param startupcost: cost to commit ($)
    :param shutdowncost: cost to de-commit ($)
    :param mustrun: flag that forces commimtent to be on

    :param name: name of the generator
    :param index: numbering of the generator    
    :param bus: bus name that the generator is connected to 
    """

    def __init__(self,kind='generic',
        Pmin=0,Pmax=500,
        minuptime=0,mindowntime=0,
        rampratemax=None,rampratemin=None,
        costcurvestring='20P',
        heatratestring=None,fuelcost=1,
        startupcost=0,shutdowncost=0,
        mustrun=False,
        name='',index=None,bus=None):
        
        update_attributes(self,locals()) #load in inputs
        if index is None: self.index=hash(self)
        if name in [None, '']: self.name = self.index+1 #1 and up naming     
        if self.rampratemin is None and self.rampratemax is not None: self.rampratemin = -1*self.rampratemax
        
        self._makeEmpties()
        self.isControllable=True
    def buildCostModel(self,num_breakpoints):
        ''' create a cost model for bidding with :meth:`~bidding.makeModel` '''
        if getattr(self,'heatratestring',None) is not None: 
            costinputs=dict(polyText=self.heatratestring,multiplier=self.fuelcost)
            self.costcurvestring=None
        else: 
            costinputs=dict(polyText=self.costcurvestring)
            self.fuelcost=1
        costinputs['num_breakpoints']=num_breakpoints
        self.costModel=bidding.makeModel(minInput=self.Pmin, maxInput=self.Pmax,inputNm='Pg',outputNm='C',**costinputs)
    def _makeEmpties(self): 
        self.variables={}
        self.constraintsD={}
        self.bid={}
    def power(self,time=None): 
        '''real power output at time'''
        return self.get_variable('power',time)
    def status(self,time): 
        '''on/off status at time'''
        return self.get_variable('status',time)
    def status_change(self,t,times): 
        if t>0: previous_status=self.status(times[t-1])
        else:   previous_status=self.status(times.initialTime)
        return self.status(times[t]) - previous_status
    def power_change(self,t,times):
        if t>0: previous_power=self.power(times[t-1])
        else:   previous_power=self.power(times.initialTime)
        return self.power(times[t])-previous_power
    def cost(self,time): 
        '''total cost at time (operating + startup + shutdown)'''
        return self.operatingcost(time)+self.cost_startup(time)+self.cost_shutdown(time)
    def cost_startup(self,time): return self.get_variable('startupcost',time)
    def cost_shutdown(self,time): return self.get_variable('shutdowncost',time) 
    def operatingcost(self,time): 
        '''cost of real power production at time (based on bid model approximation).'''
        return self.bid[time].output()
    def truecost(self,time):
        '''exact cost of real power production at time (based on exact bid polynomial).'''
        return value(self.status(time))*self.costModel.trueOutput(self.power(time))
    def incrementalcost(self,time): 
        '''change in cost with change in power at time (based on exact bid polynomial).'''
        return self.bid[time].incOutput(self.power(time)) if value(self.status(time)) else None
    def getstatus(self,t,times): return dict(u=value(self.status(t)),P=value(self.power(t)),hoursinstatus=self.gethrsinstatus(t,times))
    def gethrsinstatus(self,tm,times):
        status=value(self.status(tm))
        timesClipped=times[:times.index(tm)]
        try: 
            t_lastchange=(t for t in reversed(timesClipped) if value(self.status(t))!=status ).next()
            return hours(tm-t_lastchange)
        except StopIteration: #no changes over whole time period
            h=hours(tm-times[0])
            if value(self.status(times.initialTime)) == status: h+=self.initialStatusHours
            return h
    def t_id(self,name,time): return name.replace(' ','_')+'_'+self.iden(time)
    def get_variable(self,name,time): return self.variables[self.t_id(name,time)]
    def add_variable(self,name,short_name=None,time=None,kind='Continuous',low=-1000000,high=1000000,fixed_value=None):
        if short_name is None: short_name=name
        name=self.t_id(name,time)
        short_name=self.t_id(short_name,time)
        if fixed_value is None:
            self.variables[name] = new_variable(name=short_name,low=low,high=high,kind=kind)
        else:
            self.variables[name] = fixed_value
    def add_constraint(self,name,time,expression): self.constraintsD[self.t_id(name,time)]=expression
    def get_constraint(self,name,time): return self.constraintsD[self.t_id(name,time)]

    def add_timevars(self,times,num_breakpoints=config.default_num_breakpoints,dispatch_decommit_allowed=False):
        '''set up dicts for time-varying optimization variables
        (power,u,startup,shutdown,bid)
        '''
        self.buildCostModel(num_breakpoints=num_breakpoints)
        allvars=[]
        commitment_problem= len(times)>1 or dispatch_decommit_allowed
        for time in times:
            self.add_variable('power','P',time,low=0,high=self.Pmax)
            if commitment_problem: #UC problem
                if not self.mustrun: self.add_variable('status', 'u', time, kind='Binary')
                else: self.add_variable('status', 'u', time, fixed_value=True)
                self.add_variable('capacity', 'Pmax', time, low=0,high=self.Pmax)
                self.add_variable('startupcost','Csu',time, low=0,high=self.startupcost)
                self.add_variable('shutdowncost','Csd',time, low=0,high=self.shutdowncost)
            else: #ED or OPF problem, no commitments
                self.add_variable('status', 'u', time,fixed_value=True)
                self.add_variable('startupcost', 'Csu', time,fixed_value=0)
                self.add_variable('shutdowncost', 'Csd', time,fixed_value=0)
                
            self.bid[time]=bidding.Bid(
                model=self.costModel,
                inputvar=self.power(time),
                statusvar=self.status(time),
                iden=self.iden(time)
                )
            allvars.extend(self.bid[time].add_timevars())
        else:
            valid_variables=filter_optimization_objects(self.variables,times)
            allvars.extend(valid_variables.values())

        return allvars
    
    def update_vars(self,times,problem):
        for time in times: self.bid[time].update_vars()
        for nm,v in self.variables.items(): self.variables[nm]=value(v)
    def fix_vars(self,times,problem):
        self.update_vars(times,problem)
        self.bid={} #wipe bid info - no longer needed
    def plotCostCurve(self,P=None,filename=None): self.costModel.plot(P,filename)
    def setInitialCondition(self,time=None, P=None, u=True, hoursinstatus=100):
        if P is None: P=(self.Pmax-self.Pmin)/2 #set default power as median output
        self.add_variable('status', 'u', time, fixed_value=u)
        self.add_variable('power', 'P', time, fixed_value=P*u) #note: this eliminates ambiguity of off status with power non-zero output
        self.initialStatusHours = hoursinstatus
    def constraints(self,times):
        '''create the optimization constraints for a generator over all times'''
        def roundoff(n):
            m=int(n)
            if n!=m: raise ValueError('min up/down times must be integer number of intervals, not {}'.format(n))
            return m

        all_constraints={}
        commitment_problem= len(times)>1
                
        if commitment_problem:
            tInitial = times.initialTime
            tEnd = len(times)
            if self.minuptime>0:
                up_intervals_remaining=roundoff((self.minuptime - self.initialStatusHours)/times.intervalhrs)
                min_up_intervals_remaining_init =   min(tEnd, up_intervals_remaining*self.status(tInitial) )
            else: min_up_intervals_remaining_init=0
            if self.mindowntime>0:
                down_intervals_remaining=roundoff((self.mindowntime - self.initialStatusHours)/times.intervalhrs)
                min_down_intervals_remaining_init = min(tEnd,down_intervals_remaining*(self.status(tInitial)==0))
            else: min_down_intervals_remaining_init=0
            #initial up down time
            if min_up_intervals_remaining_init>0: 
                self.add_constraint('minuptime', tInitial, 0==sumVars([(1-self.status(times[t])) for t in range(min_up_intervals_remaining_init)]))
            if min_down_intervals_remaining_init>0: 
                self.add_constraint('mindowntime', tInitial, 0==sumVars([self.status(times[t]) for t in range(min_down_intervals_remaining_init)]))


            #initial ramp rate
            if self.rampratemax is not None:
                if self.power(tInitial) + self.rampratemax < self.Pmax:
                    E=self.power(times[0]) - self.power(tInitial) <= self.rampratemax
                    self.add_constraint('ramp lim high', tInitial, E)
                    
            if self.rampratemin is not None:
                if self.power(tInitial) + self.rampratemin > self.Pmin:
                    E=self.rampratemin <= self.power(times[0]) - self.power(tInitial)
                    self.add_constraint('ramp lim low', tInitial, E) 
            
            
            #calculate up down intervals
            min_up_intervals =  roundoff(self.minuptime/times.intervalhrs)
            min_down_intervals = roundoff(self.mindowntime/times.intervalhrs)
        
        for t,time in enumerate(times):
            #bid constraints
            
            all_constraints.update( self.bid[time].constraints() )
            #min/max power
            if self.Pmin>0: self.add_constraint('min gen power', time, self.power(time)>=self.status(time)*self.Pmin)
            self.add_constraint('max gen power', time, self.power(time)<=self.status(time)*self.Pmax)
            
            if len(times)==1: continue #if ED or OPF problem
        
            #min up time 
            if t >= min_up_intervals_remaining_init and self.minuptime>0:
                no_shut_down=range(t,min(tEnd,t+min_up_intervals))
                min_up_intervals_remaining=min(tEnd-t,min_up_intervals)
                E = sumVars([self.status(times[s]) for s in no_shut_down]) >= min_up_intervals_remaining*self.status_change(t,times)
                self.add_constraint('min up time', time, E)
            #min down time        
            if t >= min_down_intervals_remaining_init and self.mindowntime>0:
                no_start_up=range(t,min(tEnd,t+min_down_intervals))
                min_down_intervals_remaining=min(tEnd-t,min_down_intervals)
                E=sumVars([1-self.status(times[s]) for s in no_start_up]) >= min_down_intervals_remaining * -1 * self.status_change(t,times)
                self.add_constraint('min down time', time, E)
                                        
            #ramping power
            if self.rampratemax is not None:
                self.add_constraint('ramp lim high', time, self.power_change(t,times) <= self.rampratemax)
            if self.rampratemin is not None:
                self.add_constraint('ramp lim low', time,  self.rampratemin <= self.power_change(t,times) )

            #start up and shut down costs
            if self.startupcost>0:
                self.add_constraint('startup cost', time, self.cost_startup(time)>=self.startupcost*self.status_change(t, times))
            if self.shutdowncost>0:
                self.add_constraint('shutdown cost', time, self.cost_shutdown(time)>=self.shutdowncost*-1*self.status_change(t, times))
                
        all_constraints.update(filter_optimization_objects(self.constraintsD,times))
        return all_constraints        
        
    def __str__(self): return 'g{ind}'.format(ind=self.index)
    def __int__(self): return self.index
    def iden(self,t):  return str(self)+str(t)


class Generator_nonControllable(Generator):
    """ Describes a generator with a fixed schedule."""
    def __init__(self,schedule=None,
        fuelcost=1,costcurvestring='0',
        mustrun=False,
        Pmin=0,Pmax=None,
        power=None,
        name=None,index=None,bus=None,kind='wind',**kwargs):
        if power is not None and schedule is None: 
            self.schedule = FixedSchedule(P=power)
        update_attributes(self,locals(),exclude=['power']) #load in inputs
        if Pmax is None: self.Pmax = self.schedule.maxvalue
        self.isControllable=False
    def power(self,time): return self.schedule.getEnergy(time)
    def status(self,time): return True
    def setInitialCondition(self,time=None, P=None, u=None, hoursinstatus=None):
        if P is None: P=self.schedule.getEnergy(time) #set default power as first scheduled power output
        self.schedule.P[time]=P
    def getstatus(self,t,times): return dict()
    def add_timevars(self,times,num_break_points=config.default_num_breakpoints,dispatch_decommit_allowed=False):
        self.buildCostModel(num_break_points)
        return []
    def update_vars(self,times=None,problem=None): return
    def fix_timevars(self,times=None): return
    def cost(self,time): return self.operatingcost(time)
    def operatingcost(self,time): return self.costModel.trueOutput( self.power(time) )
    def truecost(self,time): return self.cost(time)
    def incrementalcost(self,time): return self.fuelcost*self.costModel.incOutput(self.power(time))
    def constraints(self,times): return #no constraints
        
class Line(object):
    """
    Describes a tranmission line. Currently the model
    only considers real power flow under normal conditions.
    
    :param From: name of bus line originates at
    :param To:   name of bus line connects to
    :param X:    line reactance (p.u.)
    :param Pmax: maximum (positive direction) power flow over line
    :param Pmin: maximum (negative direction) power flow over line.
      Defaults to -:attr:`Pmax` if not specified.
    """
    def __init__(self,name='',index=None,From=None,To=None,X=0.05,Pmax=9999,Pmin=None,**kwargs):
        update_attributes(self,locals()) #load in inputs
        if index is None: self.index=hash(self)
        if self.Pmin is None: self.Pmin=-self.Pmax #reset default to be -Pmax
        self.P,self.price=dict(),dict()
    def add_timevars(self,times):
        for time in times: 
            self.P[time]=new_variable(name='P_'+self.iden(time))
        return self.P.values()
    def update_vars(self,times,problem):
        for time in times: self.P[time]=value(self.P[time],problem)
    def constraints(self,times,buses):
        '''create the constraints for a line over all times'''
        constraints=dict()
        for t in times:
            iden = self.iden(t)
            busNames=getattrL(buses,'name')
            iFrom,iTo=busNames.index(self.From),busNames.index(self.To)
            constraints['lineFlow_'+iden]=     self.P[t] == (1/self.X) * sumVars([ buses[iFrom].angle(t),-1*buses[iTo].angle(t) ])
            constraints['lineLimitHi_'+iden]=  self.P[t]<=self.Pmax
            constraints['lineLimitLow_'+iden]= self.Pmin<=self.P[t]
        return constraints
    
    def __str__(self): return 'k{ind}'.format(ind=self.index)
    def __int__(self): return self.index
    def iden(self,t): return str(self)+str(t)
    def getprice(self,time,problem):
        #get congestion price on line
        return problem.dual('lineFlow_'+self.iden(time)) #problem.dual('lineLimitHi_'+self.iden(time))+problem.dual('lineLimitLow_'+self.iden(time))    


class Bus(OptimizationObject):
    """
    Describes a bus (usually a substation where one or more
    tranmission lines start/end).
    
    :param isSwing: flag if the bus is the swing bus 
      (sets the reference angle for the system)
    """
    def __init__(self,name=None,index=None,isSwing=False):
        update_attributes(self,locals()) #load in inputs
        self.generators,self.loads=[],[]
        self.init_optimization()
    
    def angle(self,time): return self.get_variable('angle',time)
    def price(self,time): return self.get_constraint('power balance',time).dual
    def create_variables(self,times):
        for time in times: self.add_variable('angle',time=time)
        return self.variables
        
    def __str__(self):  return 'i{ind}'.format(ind=self.index)
    def iden(self,t):   return str(self)+str(t)
    def Pgen(self,t):   return sumVars([gen.power(t) for gen in self.generators])
    def Pload(self,t):  return sumVars([ ld.power(t) for ld in self.loads])
    
    def powerBalance(self,t,Bmatrix,allBuses):
        if len(allBuses)==1: lineFlowsFromBus=0
        else: lineFlowsFromBus=sumVars([Bmatrix[self.index][otherBus.index]*otherBus.angle(t) for otherBus in allBuses]) #P_{ij}=sum_{i} B_{ij}*theta_j ???
        return sumVars([ -lineFlowsFromBus,-self.Pload(t),self.Pgen(t) ])
    def create_constraints(self,times,Bmatrix,buses):
        '''create the constraints for a bus over all times'''
        nBus=len(buses)
        for time in times:
            self.add_constraint('power balance',time, self.powerBalance(time,Bmatrix,buses)==0) #power balance must be zero
            if nBus>1 and self.isSwing: 
                self.add_constraint('swing bus',time, self.angle(time)==0)#swing bus has angle=0
        return self.constraints
        
def make_buses_list(loads,generators):
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
        newBus=Bus(name=busNm,index=b)
        for gen in generators: 
            if gen.bus==newBus.name: newBus.generators.append(gen) 
            if not swingHasBeenSet: newBus.isSwing=swingHasBeenSet=True
        for ld in loads: 
            if ld.bus==newBus.name: newBus.loads.append(ld)             
        buses.append(newBus)
    return buses


class Load(object):
    """
    Describes a power system load (demand).
    Currently only real power is considered.
    
    :param bus: name of bus that load is on 
      (not required if ED/OPF problem)
    :param schedule: :class:`~schedule.Schedule` object
      (generally created automatically from file
      by :meth:`get_data.build_class_list`)
    """
    def __init__(self,kind='varying',name=None,index=None,bus=None,schedule=None):
        update_attributes(self,locals()) #load in inputs
        self.dispatched_power = dict()
    def power(self,time=None): return self.dispatched_power[time] #self.schedule.getEnergy(time)
    def __str__(self): return 'd{ind}'.format(ind=self.index)    
    def __int__(self): return self.index
    def iden(self,t):     return str(self)+str(t)
    def benifit(self,time=None): return (self.power(time) - self.schedule.getEnergy(time))*config.cost_loadshedding
    def shed(self,time): return self.schedule.getEnergy(time)- value(self.power(time)) #power_to_energy(value(self.power(time)),time)
    def add_timevars(self,times=None,shedding_allowed=False):
        if shedding_allowed: 
            for t in times: self.dispatched_power[t]=new_variable('Pd_{}'.format(self.iden(t)),low=0,high=self.schedule.getEnergy(t))
        else:
            for t in times: self.dispatched_power[t]=self.schedule.getEnergy(t)
        return self.dispatched_power.values()
    
    def update_vars(self,times,problem):
        for t in times: self.dispatched_power[t]=value(self.dispatched_power[t],problem)

    def constraints(self,*args): return #no constraints
    
class Load_Fixed(Load):
    """
    Describes a load that does not vary with time.
    This can be an easy way to add a load for an ED/OPF problem,
    or a system baseload.
    
    :param P: real power consumed by load (MW/hr)
    """
    def __init__(self,kind='fixed',name=None,index=None,bus=None,P=0):
        update_attributes(self,locals()) #load in inputs
        if index is None: self.index=hash(self)
        self.Pfixed = self.P
        del self.P
        self.dispatched_power = dict()
    def power(self,time=None): return self.dispatched_power[time]
    def add_timevars(self,times=None,shedding_allowed=False):
        if shedding_allowed: 
            for t in times: self.dispatched_power[t]=new_variable('Pd_{}'.format(self.iden(t)),low=0,high=self.schedule.getEnergy(t))
            return self.dispatched_power.values()
        else:
            for t in times: self.dispatched_power[t]=self.Pfixed
            return []
        
    def benifit(self,time=None): return (self.power(time) - self.Pfixed)*config.cost_loadshedding
    
class Network(object):
    """
    Creates and contains the admittance matrix (B)
    used in calculating the power balance for OPF problems.
    
    :param buses: list of :class:`~powersystems.Line` objects
    :param lines: list of :class:`~powersystems.Bus` objects
    """
    def __init__(self,buses,lines):
        self.buses=buses
        self.lines=lines
        self.createBmatrix()
    def createBmatrix(self):
        '''create the matrix B: total admittance from bus i to j'''
        nB=len(self.buses)
        self.Bmatrix=numpy.zeros((nB,nB))
        namesL=[bus.name for bus in self.buses]
        for line in self.lines:
            busFrom=self.buses[namesL.index(line.From)]
            busTo=self.buses[namesL.index(line.To)]
            self.Bmatrix[busFrom.index,busTo.index]+=-1/line.X
            self.Bmatrix[busTo.index,busFrom.index]+=-1/line.X
        for i in range(0,nB): 
            self.Bmatrix[i,i]=-1*sum(self.Bmatrix[i,:])

def power_to_energy(P,time):
    return P*time.intervalhrs
    
def filter_optimization_objects(objects,times):
    times_str=[str(t).lstrip('t') for t in times]
    times_str.append(str(times.initialTime).lstrip('t'))
    def valid(name,val):
        in_time_period=name.rsplit('t',1)[1] in times_str
        is_variable_not_fixed = getattr(val,'value',0)==None
        return in_time_period and is_variable_not_fixed
    return dict(filter(lambda (name,val): valid(name,val) ,objects.items()))
