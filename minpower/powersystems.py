"""
Defines models for power systems concepts: 
:class:`~powersystems.Bus`, :class:`~powersystems.Generator`, 
:class:`~powersystems.Line`, and :class:`~powersystems.Load`.
"""
import bidding
from optimization import newVar,value,sumVars
#from schedule import *
from commonscripts import hours,subset,subsetexcept,drop_case_spaces,getattrL
import config
import logging

from dateutil.relativedelta import relativedelta
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
    if kind=='wind' or not kwargs['isControllable']: 
        classname=Generator_nonControllable
    else: classname=Generator
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
        rampratemax=1000,rampratemin=None,
        costcurvestring='20P',
        heatratestring=None,fuelcost=1,
        startupcost=0,shutdowncost=0,
        mustrun=False,
        name=None,index=None,bus=None):
        
        vars(self).update(locals()) #load in inputs
        if index is None: index=hash(self)        
        if self.rampratemin is None: self.rampratemin = -1*self.rampratemax
        
        self.buildCostModel()
        self._makeEmpties()
        self.isControllable=True
    def buildCostModel(self):
        ''' create a cost model for bidding with :class:`~bidding.PWLmodel` '''
        if getattr(self,'heatratestring',None) is not None: 
            costinputs=dict(polyText=self.heatratestring,multiplier=self.fuelcost)
            self.costcurvestring=None
        else: 
            costinputs=dict(polyText=self.costcurvestring)
            self.fuelcost=1
        self.costModel=bidding.PWLmodel(minInput=self.Pmin, maxInput=self.Pmax,inputNm='Pg',outputNm='C',**costinputs)
    def _makeEmpties(self): self.u,self.power,self.bid,self.startup,self.shutdown=dict(),dict(),dict(),dict(),dict()
        
    def P(self,time=None): 
        '''real power output at time'''
        return self.power[time]
    def cost(self,time): 
        '''total cost at time (operating + startup + shutdown)'''
        return self.operatingcost(time)+self.startupcost*self.startup[time]+self.shutdowncost*self.shutdown[time]
    def operatingcost(self,time): 
        '''cost of real power production at time (based on bid model approximation).'''
        return self.bid[time].output()
    def truecost(self,time):
        '''exact cost of real power production at time (based on exact bid polynomial).'''
        return value(self.u[time])*self.bid[time].trueOutput(self.P(time))
    def incrementalcost(self,time): 
        '''change in cost with change in power at time (based on exact bid polynomial).'''
        return self.bid[time].incOutput(self.P(time)) if value(self.u[time]) else None
    def getstatus(self,t,times): return dict(u=value(self.u[t]),P=value(self.P(t)),hoursinstatus=self.gethrsinstatus(t,times))
    def gethrsinstatus(self,tm,times):
        status=value(self.u[tm])
        timesClipped=times[:times.index(tm)]
        try: 
            t_lastchange=(t for t in reversed(timesClipped) if value(self.u[t])!=status ).next()
            return hours(tm-t_lastchange)
        except StopIteration: #no changes over whole time period
            h=hours(tm-times[0])
            if value(self.u[times.initialTime]) == status: h+=self.initialStatusHours
            return h
        
    def add_timevars(self,times):
        '''set up dicts for time-varying optimization variables
        (power,u,startup,shutdown,bid)
        '''
        commitment_problem= len(times)>1
        for time in times:    
            iden=self.iden(time)
            self.power[time]=newVar(name='P_'+iden,low=self.Pmin,high=self.Pmax)
            self.bid[time]=bidding.Bid(model=self.costModel,iden=self.iden(time))
            
            if commitment_problem: #UC problem
                self.u[time]=newVar(name='u_'+iden,kind='Binary')
                self.startup[time] =newVar(name='su_'+iden,kind='Binary')
                self.shutdown[time]=newVar(name='sd_'+iden,kind='Binary')
            else: #ED or OPF problem - no commitments
                self.u[time]=True
                self.startup[time]=False
                self.shutdown[time]=False
            
    def plotCostCurve(self,P=None,filename=None): self.costModel.plot(P,filename)
    def setInitialCondition(self,time=None, P=None, u=True, hoursinstatus=100):
        if P is None: P=(self.Pmax-self.Pmin)/2 #set default power as median output
        self.u[time]=u
        self.power[time]=P*u  #note: this eliminates ambiguity of off status with power non-zero output
        self.initialStatusHours = hoursinstatus
        self.startup[time]= True if self.initialStatusHours==0 and self.u[time] else False
        self.shutdown[time]=True if self.initialStatusHours==0 and not self.u[time] else False

    def constraints(self,times):
        '''create the optimization constraints for a generator over all times'''
        constraintsD=dict()
        
        if len(times)>1:
            iden='{g}_init'.format(g=str(self))
            #initial time
            tInitial = times.initialTime
            startTime = times[0].Start
            tEndHours = relativedelta(times[-1].Start, times[0].Start).hours
            tEndIndex = len(times)
            minUpHoursRemainingInit = max(0, (self.u[tInitial]==1) * min(tEndHours, self.minuptime - self.initialStatusHours))
            minDnHoursRemainingInit = max(0, (self.u[tInitial]==0) * min(tEndHours, self.mindowntime - self.initialStatusHours))
            #initial up down time
            if minUpHoursRemainingInit>0: constraintsD['minuptime_'+iden]= 0==sumVars([(1-self.u[times[t]]) for t in range(0,minUpHoursRemainingInit)])
            if minDnHoursRemainingInit>0: constraintsD['mindowntime_'+iden]= 0==sumVars([self.u[times[t]] for t in range(0,minDnHoursRemainingInit)])
            #initial start up / shut down
            constraintsD['statusChange_'+iden]= self.startup[times[0]]-self.shutdown[times[0]] == self.u[times[0]] - self.u[tInitial]
            #initial ramp rate
            constraintsD['rampingLimHi_'+iden]=                     self.P(times[0]) - self.P(tInitial) <= self.rampratemax
            constraintsD['rampingLimLo_'+iden]= self.rampratemin <=     self.P(times[0]) - self.P(tInitial)
        else: #fix status for ED,OPF problems
            if not self.u[times[0]]==False: self.u[times[0]]=True
        
        for t,time in enumerate(times):
            iden=self.iden(time)
            #must run
            if self.mustrun: self.u[time] = True #overwrite the variable with a true
            #bid constraints
            bidConstraints=self.bid[time].constraints(inputVar=self.P(time),status=self.u[time])
            constraintsD.update( bidConstraints )
            #min/max power
            constraintsD['min-gen-power_'+iden]= self.P(time)>=self.u[time]*self.Pmin
            constraintsD['max-gen-power_'+iden]= self.P(time)<=self.u[time]*self.Pmax
            if len(times)>1: #if UC or SCUC problem
                #start up / shut down
                constraintsD['statusConstant_'+iden]=       self.startup[time]+self.shutdown[time] <= 1
                if t>0: constraintsD['statusChange_'+iden]= self.startup[time]-self.shutdown[time] == self.u[time] - self.u[times[t-1]]
                #up/down time minimums 
                if relativedelta(time.Start, startTime).hours > minUpHoursRemainingInit:
                    constraintsD['minuptime_'+iden]= 1 >= self.startup[time]  + sumVars([self.shutdown[times[s]] for s in range(t,min(tEndIndex,t+self.minuptime))])
                if relativedelta(time.Start, startTime).hours > minDnHoursRemainingInit:                
                    constraintsD['mindowntime_'+iden]= 1 >= self.shutdown[time] + sumVars([ self.startup[times[s]] for s in range(t,min(tEndIndex,t+self.mindowntime))])
                #ramping power
                if t>0:
                    constraintsD['rampingLimHi_'+iden]=                     self.P(time) - self.P(times[t-1]) <= self.rampratemax
                    constraintsD['rampingLimLo_'+iden]= self.rampratemin <=     self.P(time) - self.P(times[t-1])

        return constraintsD        
        
    def __str__(self): return 'g{ind}'.format(ind=self.index)
    def __int__(self): return self.index
    def iden(self,t):  return str(self)+str(t)


class Generator_nonControllable(Generator):
    """ Describes a generator with a fixed schedule."""
    def __init__(self,schedule=None,
        fuelcost=1,costcurvestring='0',
        mustrun=False,
        Pmin=0,Pmax=None,
        name=None,index=None,bus=None,**kwargs):
        vars(self).update(locals()) #load in inputs
        if Pmax is None: self.Pmax = self.schedule.maxvalue
        self.buildCostModel()
        self.isControllable=False
        
    def P(self,time): return self.schedule.getEnergy(time)
    def setInitialCondition(self,time=None, P=None, u=None, hoursinstatus=None):
        if P is None: P=self.schedule.getEnergy(self.schedule.times[0]) #set default power as first scheduled power output
        self.schedule.P[time]=P
    def getstatus(self,t,times): return dict()
    def add_timevars(self,times): return
    def cost(self,time): return self.operatingcost(time)
    def operatingcost(self,time): return self.fuelcost*self.costModel.trueOutput( self.P(time) )
    def truecost(self,time): return self.cost(time)
    def incrementalcost(self,time): return self.fuelcost*self.costModel.incOutput(self.P(time))
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
        vars(self).update(locals()) #load in inputs
        if self.Pmin is None: self.Pmin=-self.Pmax #reset default to be -Pmax
        self.P=dict()
    def add_timevars(self,times):
        for time in times: 
            self.P[time]=newVar(name='P_'+self.iden(time))
        return self.P
    def constraints(self,times,buses):
        '''create the constraints for a line over all times'''
        constraints=dict()
        for t in times:
            iden = self.iden(t)
            busNames=getattrL(buses,'name')
            iFrom,iTo=busNames.index(self.From),busNames.index(self.To)
            constraints['lineFlow '+iden]=     self.P[t] == (1/self.X) * sumVars([ buses[iFrom].angle[t],-1*buses[iTo].angle[t] ])
            constraints['lineLimitHi '+iden]=  self.P[t]<=self.Pmax
            constraints['lineLimitLow '+iden]= self.Pmin<=self.P[t]
        return constraints
    
    def __str__(self): return 'k{ind}'.format(ind=self.index)
    def __int__(self): return self.index
    def iden(self,t): return str(self)+str(t)
    
class Bus(object):
    """
    Describes a bus (usually a substation where one or more
    tranmission lines start/end).
    
    :param isSwing: flag if the bus is the swing bus 
      (sets the reference angle for the system)
    """
    def __init__(self,name=None,index=None,isSwing=False):
        vars(self).update(locals()) #load in inputs
        self.generators,self.loads=[],[]
        self.angle,self.price=dict(),dict()
    def add_timevars(self,times):
        for time in times: self.addTimeElement(time=time,angle=newVar(name='angle_'+self.iden(time)))        
    def addTimeElement(self,time=None,angle=None): self.angle[time]=angle
    def __str__(self):     return 'i{ind}'.format(ind=self.index)    
    def __int__(self):    return self.index
    def iden(self,t):        return str(self)+str(t)
    def Pgen(self,t):   return sumVars([gen.P(t) for gen in self.generators])
    def Pload(self,t):  return sumVars([ ld.P(t) for ld in self.loads])
        
    def constraints(self,times,Bmatrix,buses):
        '''create the constraints for a bus over all times'''
        def powerBalance(self,t,Bmatrix,allBuses):
            if len(allBuses)==1: lineFlowsFromBus=0
            else: lineFlowsFromBus=sumVars([Bmatrix[self.index][otherBus.index]*otherBus.angle[t] for otherBus in allBuses]) #P_{ij}=sum_{i} B_{ij}*theta_j ???
            return sumVars([ -lineFlowsFromBus,-self.Pload(t),self.Pgen(t) ])

        constraints=dict()
        nBus=len(buses)
        for t in times:
            iden=self.iden(t)
            if nBus>1 and self.isSwing: constraints['swingBus '+iden] = self.angle[t]==0 #swing bus has angle=0
            constraints['powerBalance '+iden] = powerBalance(self,t,Bmatrix,buses)==0 #power balance must be zero
        return constraints

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
        vars(self).update(locals()) #load in inputs
    def P(self,time=None): return self.schedule.getEnergy(time)
    def __str__(self): return 'd{ind}'.format(ind=self.index)    
    def __int__(self): return self.index
    def iden(self,t):     return str(self)+str(t)
    def benifit(self,time=None): return 0
    def add_timevars(self,times=None): return
    def constraints(self,*args): return #no constraints
    
class Load_Fixed(Load):
    """
    Describes a load that does not vary with time.
    This can be an easy way to add a load for an ED/OPF problem,
    or a system baseload.
    
    :param P: real power consumed by load (MW/hr)
    """
    def __init__(self,kind='fixed',name=None,index=None,bus=None,P=0):
        vars(self).update(locals()) #load in inputs
        self.Pfixed = self.P
        del self.P
    def P(self,time=None): return self.Pfixed

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
