"""
Defines models for power systems components, including 
:class:`~powersystems.PowerSystem`, :class:`~powersystems.Bus`, 
:class:`~powersystems.Generator`, :class:`~powersystems.Load`,
and  :class:`~powersystems.Line`. Each of these objects inherits
an optimization framework from :class:`~optimization.OptimizationObject`.
"""
<<<<<<< HEAD
import bidding
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> add non-controllable gen to ED. added remote script- not yet working.
from optimization import newVar,value,sumVars
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
from commonscripts import hours,subset,subsetexcept,drop_case_spaces,getattrL,flatten
<<<<<<< HEAD
=======
from optimization import newVar,value,sumVars,dual
#from schedule import *
<<<<<<< HEAD
from commonscripts import hours,subset,subsetexcept,drop_case_spaces,getattrL
>>>>>>> added status method for Generator() and getprice for bus().
=======
=======
from optimization import newVar,value,sumVars
>>>>>>> working coopr and pulp mix
from commonscripts import hours,subset,subsetexcept,drop_case_spaces,getattrL,flatten
>>>>>>> duals and variables now working with coopr. tests are still failing.
=======
=======
from optimization import newVar,value,sumVars,OptimizationObject
>>>>>>> this is going to be a major refactor. putting on hold for now.
from commonscripts import hours,subset,subsetexcept,drop_case_spaces,getattrL,flatten,unique
>>>>>>> added OPF testing
import config
import logging,math
=======
=======
from commonscripts import hours,drop_case_spaces,getattrL,unique
>>>>>>> default name for generator based on index
=======
=======
from optimization import new_variable,value,sumVars
>>>>>>> renamed newVar to new_variable
=======
from optimization import new_variable,value,sum_vars,OptimizationObject
>>>>>>> refactored powersystems. moving on to bidding
=======
from optimization import value,sum_vars,OptimizationObject
>>>>>>> first working pass through solver (results still needs major rework
=======
from optimization import value,dual,sum_vars,OptimizationObject
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> cleared up dual problem (old coopr solution index=None)
from commonscripts import hours,drop_case_spaces,getattrL,unique,update_attributes
>>>>>>> added update_attributes function for classes. fixed power attr/method clash for gen_noncontrollable
=======
from commonscripts import hours,drop_case_spaces,flatten,getattrL,unique,update_attributes
>>>>>>> had to add line constraints to PowerSystems object. line constraints needed slight notation debug.
import config, bidding
from schedule import FixedSchedule
import logging
<<<<<<< HEAD
>>>>>>> add non-controllable gen to ED. added remote script- not yet working.

#from dateutil.relativedelta import relativedelta
=======
>>>>>>> documentation overhaul - up to schedule
=======
=======
from optimization import value,dual,OptimizationObject
>>>>>>> merged in changes from DR_model
=======
from optimization import value,dual,OptimizationObject,OptimizationProblem
>>>>>>> basic conversion of power_system to OptimziationProblem object
from commonscripts import hours,drop_case_spaces,flatten,getattrL,unique,update_attributes,show_clock
import config, bidding
from schedule import FixedSchedule
import logging
<<<<<<< HEAD
import threading
>>>>>>> debugging times for problem creation
=======
#import threading
>>>>>>> cleanup
import numpy 

def makeGenerator(kind='generic',**kwargs):
    """
    Create a :class:`~powersystems.Generator` object 
    (or a :class:`~powersystems.Generator_nonControllable`
    object depending on the kind). Set defaults
    depending on the kind (default values come from :mod:`config`).
    
    :param kind: define the kind of generator (all 
        kinds are defined in :data:`config.generator_kinds`)
    
    Other parameters are detailed in :class:`~powersystems.Generator`.
    
    :returns: a :class:`~powersystems.Generator` object
    """

    def parse_args(kind,**inputs):
        '''check kind pull defaults from the config file'''
        kind=drop_case_spaces(kind)
        if kind not in config.generator_kinds:
            logging.info('"{k}" is an unknown kind of generator, using generic defaults.'.format(k=kind))
            kind='generic'
        
        ignore_names=['power','is_controllable','costcurvestring']
        
        #get defaults from config file
        defaults=dict()
        for name,val in config.generator_defaults.iteritems():
            try: defaults[name]=val[kind]
            except KeyError:
                if inputs.get(name,None) in ['',None] and name not in ignore_names: logging.debug('no {d} default found for kind "{k}", using default from generic.'.format(d=name,k=kind))
                defaults[name]=val['generic']
            except TypeError: 
                defaults[name]=val #no kind-distincted defaults
                
        #use the values that are defined in the inputs
        outputs=defaults
        outputs.update(inputs)
        return kind,outputs
    
    
    kind,kwargs=parse_args(kind,**kwargs)    
    if kind=='wind' or not kwargs['is_controllable'] or kwargs.get('schedule',None) or (kwargs.get('power') is not None): 
        classname=Generator_nonControllable
    else:
        classname=Generator
        kwargs.pop('power')

    kwargs.pop('is_controllable')

    return classname(kind=kind,**kwargs)

def makeLoad(kind='varying',**kwargs):
    """
    Create a :class:`~powersystems.Load` object (if a power 
    :class:`~schedule.Schedule` is specified) or a
    cost_load_sheddingrsystems.Load_Fixed` object (if a single
    power value :attr:`P` is specified).
    """
    if 'P' in kwargs.keys(): return Load_Fixed(kind=kind, **kwargs)
    else: return Load(kind=kind,**kwargs)
        
class Generator(OptimizationObject):
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
        name='',index=None,bus=None,
        dispatch_decommit_allowed=False):
        
        update_attributes(self,locals()) #load in inputs     
        if self.rampratemin is None and self.rampratemax is not None: self.rampratemin = -1*self.rampratemax
        self.is_controllable=True
        self.build_cost_model()
        self.init_optimization()
        
    def power(self,time=None): 
        '''real power output at time'''
        return self.get_variable('power',time,indexed=True)
    def status(self,time): 
        '''on/off status at time'''
        return self.get_variable('status',time,indexed=True)
    def status_change(self,t,times): 
        '''is the unit changing status between t and t-1'''
        if t>0: previous_status=self.status(times[t-1])
        else:   previous_status=self.initial_status
        return self.status(times[t]) - previous_status
    def power_change(self,t,times):
        '''change in output between power between t and t-1'''
        if t>0: previous_power=self.power(times[t-1])
        else:   previous_power=self.power(times.initialTime)
        return self.power(times[t])-previous_power
    def cost(self,time): 
        '''total cost at time (operating + startup + shutdown)'''
        return self.operatingcost(time)+self.cost_startup(time)+self.cost_shutdown(time)
<<<<<<< HEAD
    def cost_startup(self,time): return self.get_variable('startupcost',time) if self.startupcost!=0 else 0
    def cost_shutdown(self,time): return self.get_variable('shutdowncost',time) if self.shutdowncost!=0 else 0
=======
    def cost_startup(self,time): return self.get_variable('startupcost',time,indexed=True)
    def cost_shutdown(self,time): return self.get_variable('shutdowncost',time,indexed=True) 
>>>>>>> major overahual on setting up variables/constraints directly to the parent problem. this allows the use of sets, variable lists. still need to cleanup (including dual values).
    def operatingcost(self,time): 
        '''cost of real power production at time (based on bid model approximation).'''
        return self.bid(time).output()
    def cost_first_stage(self,times):
        return sum(self.cost_startup(time)+self.cost_shutdown(time) for time in times)
    def cost_second_stage(self,times): return sum(self.operatingcost(time) for time in times)
    
    def truecost(self,time):
        '''exact cost of real power production at time (based on exact bid polynomial).'''
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
        return self.bid[time].trueOutput(self.P(time))
=======
        return value(self.u[time])*self.costModel.trueOutput(self.P(time))
>>>>>>> switched true cost reporting over from bid to cost model
=======
        return value(self.status(time))*self.costModel.trueOutput(self.power(time))
>>>>>>> reformulation of startup,shutdown variables according to Arroyo and Carrion 2006
=======
        return value(self.status(time))*self.cost_model.output_true(self.power(time))
>>>>>>> refactored powersystems. moving on to bidding
    def incrementalcost(self,time): 
        '''change in cost with change in power at time (based on exact bid polynomial).'''
        return self.bid(time).output_incremental(self.power(time)) if value(self.status(time)) else None
    def bid(self,time):
        ''':class:`~bidding.Bid` object for time'''
        return self.get_child('bids', time) 
    def getstatus(self,t,times): return dict(u=value(self.status(t)),P=value(self.power(t)),hoursinstatus=self.gethrsinstatus(t,times))
    def plot_cost_curve(self,P=None,filename=None): self.cost_model.plot(P,filename)
    def gethrsinstatus(self,tm,times):
        if not self.is_controllable: return None
        status=value(self.status(tm))
        timesClipped=times[:times.index(tm)]
        try: 
            t_lastchange=(t for t in reversed(timesClipped) if value(self.status(t))!=status ).next()
            return hours(tm.End-t_lastchange.Start)
        except StopIteration: #no changes over whole time period
            h=hours(tm.End-times[0].Start)
            if value(self.status(times.initialTime)) == status: h+=self.initial_status_hours
            return h
    
    def set_initial_condition(self,time=None, P=None, u=True, hoursinstatus=100):
        '''Set the initial condition at time.'''
        if P is None: P=(self.Pmax-self.Pmin)/2 #set default power as median output
        self.initial_status=u
        self.initial_power =P*u #note: this eliminates ambiguity of off status with power non-zero output
        self.initial_status_hours = hoursinstatus
    def build_cost_model(self):
        ''' create a cost model for bidding with :meth:`~bidding.makeModel` '''
        if getattr(self,'heatratestring',None) is not None: 
            costinputs=dict(polyText=self.heatratestring,multiplier=self.fuelcost)
            self.costcurvestring=None
        else: 
            costinputs=dict(polyText=self.costcurvestring)
            self.fuelcost=1
        
        self.cost_model=bidding.makeModel(min_input=self.Pmin, max_input=self.Pmax,input_name='Pg',output_name='C',**costinputs)

    def create_variables(self,times):
        '''
        Create the optimization variables for a generator over all times. 
        Also create the :class:`bidding.Bid` objects.
        '''
        commitment_problem= len(times)>1 or self.dispatch_decommit_allowed
<<<<<<< HEAD
        for time in times:
            self.add_variable('power','P',time,low=0,high=self.Pmax)
            if commitment_problem: #UC problem
                if not self.mustrun: self.add_variable('status', 'u', time, kind='Binary')
                else: self.add_variable('status', 'u', time, fixed_value=True)
                self.add_variable('capacity', 'Pmax', time, low=0,high=self.Pmax)
                if self.startupcost!=0: self.add_variable('startupcost','Csu',time, low=0,high=self.startupcost)
                else: self.add_variable('startupcost','Csu',time, fixed_value=0)
                if self.shutdowncost!=0: self.add_variable('shutdowncost','Csd',time, low=0,high=self.shutdowncost)
                else: self.add_variable('shutdowncost','Csd',time, fixed_value=0)
            else: #ED or OPF problem, no commitments
<<<<<<< HEAD
<<<<<<< HEAD
                self.u[time]=True
                self.startup[time]=False
                self.shutdown[time]=False
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
                self.variables['status'][time]=True
<<<<<<< HEAD
                #self.variables['startup'][time]=False
                #self.variables['shutdown'][time]=False
>>>>>>> reformulation of startup,shutdown variables according to Arroyo and Carrion 2006
=======
                self.variables['startupcost'][time]=0
                self.variables['shutdowncost'][time]=0
>>>>>>> implemented min up down times. need to add current capacity var and finish integration testing

=======
                self.add_variable('status', 'u', time,fixed_value=True)
                self.add_variable('startupcost', 'Csu', time,fixed_value=0)
                self.add_variable('shutdowncost', 'Csd', time,fixed_value=0)
<<<<<<< HEAD
<<<<<<< HEAD
                
<<<<<<< HEAD
>>>>>>> rough optimization object model for generator. unit and integration tested.
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

>>>>>>> cleaner handling of different bid models. fix for the convex bid model, due to confusion from ugly code.
        return allvars
    
    def update_vars(self,times,problem):
<<<<<<< HEAD
        for time in times:
            self.bid[time].update_vars()
        for nm,timevar in self.variables.items():
            for tm,var in timevar.items():
<<<<<<< HEAD
                self.variables[nm][tm]=value(var)
                 
            
#            self.power[time] = value(self.power[time])
#            #if commitment_problem: #UC problem
#            self.status(time)=value(self.status(time))
#            self.startup(time) =value(self.startup(time))
#            self.shutdown(time)=value(self.shutdown(time))
            
        
<<<<<<< HEAD
<<<<<<< HEAD
=======
    def fix_timevars(self,times):
        for time in times:
            self.power[time]   =value(self.power[time])
            self.u[time]       =value(self.u[time]) ==1
            self.startup[time] =value(self.startup[time])==1
            self.shutdown[time]=value(self.shutdown[time])==1
        else: self.bid={} #wipe bid info - no longer needed
>>>>>>> added load shedding to insure feasibility
=======
            
=======
>>>>>>> working startup and shutdown constraints
    def fix_vars(self,times,problem):
        self.update_vars(times,problem)
        self.bid={} #wipe bid info - no longer needed

>>>>>>> changed fix_timevars to fix_vars in Generator(). fixed reporting on load shedding.
=======
                self.variables[nm][tm]=value(var)            
=======
        for time in times: self.bid[time].update_vars()
        for nm,v in self.variables.items(): self.variables[nm]=value(v)
>>>>>>> rough optimization object model for generator. unit and integration tested.
=======
            self.add_component('bid',time,
                bidding.Bid(
                    model=self.costModel,
=======
            
=======
>>>>>>> debugging times for problem creation
            bid=bidding.Bid(
=======

        self.add_variable('power', index=times.set, low=0, high=self.Pmax)
        
        if commitment_problem:
            self.add_variable('status', index=times.set, kind='Binary',fixed_value=True if self.mustrun else None)
            self.add_variable('capacity',index=times.set, low=0,high=self.Pmax)
            self.add_variable('startupcost',index=times.set, low=0,high=self.startupcost, fixed_value=0 if self.startupcost==0 else None)
            self.add_variable('shutdowncost',index=times.set, low=0,high=self.shutdowncost, fixed_value=0 if self.shutdowncost==0 else None)
        else: #ED or OPF problem, no commitments
            t=times[0]
            self.add_variable('status',       time=t,fixed_value=True)
            self.add_variable('startupcost',  time=t,fixed_value=0)
            self.add_variable('shutdowncost', time=t,fixed_value=0)

        bids=dict(zip(times,[bidding.Bid(
>>>>>>> major overahual on setting up variables/constraints directly to the parent problem. this allows the use of sets, variable lists. still need to cleanup (including dual values).
                    model=self.cost_model,
<<<<<<< HEAD
>>>>>>> refactored powersystems. moving on to bidding
                    inputvar=self.power(time),
                    statusvar=self.status(time),
=======
                    time=time,
                    input_var=self.power(time),
                    status_var=self.status(time),
>>>>>>> first working pass through solver (results still needs major rework
                    owner_iden=str(self),
                    time_iden=str(time)) for time in times]))
        self.add_children(bids,'bids')
        for time in times: self.bid(time).create_variables()
        #logging.debug('created {} variables {}'.format(str(self),show_clock()))
<<<<<<< HEAD
        return self.all_variables(times)
<<<<<<< HEAD
    
<<<<<<< HEAD
>>>>>>> working on the big refactor to opt.obj. model
    def fix_vars(self,times,problem):
        self.update_vars(times,problem)
        self.bid={} #wipe bid info - no longer needed
>>>>>>> fix for linear cost curves - now: cost=a*u+b*P
    def plotCostCurve(self,P=None,filename=None): self.costModel.plot(P,filename)
    def setInitialCondition(self,time=None, P=None, u=True, hoursinstatus=100):
        if P is None: P=(self.Pmax-self.Pmin)/2 #set default power as median output
        self.add_variable('status', 'u', time, fixed_value=u)
        self.add_variable('power', 'P', time, fixed_value=P*u) #note: this eliminates ambiguity of off status with power non-zero output
        self.initialStatusHours = hoursinstatus
=======
=======
=======
        return
>>>>>>> major overahual on setting up variables/constraints directly to the parent problem. this allows the use of sets, variable lists. still need to cleanup (including dual values).
    def create_objective(self,times):
<<<<<<< HEAD
        self.objective=sum_vars(self.cost(time) for time in times)
        return self.objective
>>>>>>> added create_objective method across opt obj classes. need to test.
=======
        return sum(self.cost(time) for time in times)
>>>>>>> merged in changes from DR_model

>>>>>>> refactored powersystems. moving on to bidding
    def create_constraints(self,times):
        '''create the optimization constraints for a generator over all times'''
        def roundoff(n):
            m=int(n)
            if n!=m: raise ValueError('min up/down times must be integer number of intervals, not {}'.format(n))
            return m

        commitment_problem= len(times)>1        
        if commitment_problem:
            tInitial = times.initialTime
            tEnd = len(times)
            if self.minuptime>0:
                up_intervals_remaining=roundoff((self.minuptime - self.initial_status_hours)/times.intervalhrs)
                min_up_intervals_remaining_init =   int(min(tEnd, up_intervals_remaining*self.initial_status ))
            else: min_up_intervals_remaining_init=0
            if self.mindowntime>0:
                down_intervals_remaining=roundoff((self.mindowntime - self.initial_status_hours)/times.intervalhrs)
                min_down_intervals_remaining_init = int(min(tEnd,down_intervals_remaining*(self.initial_status==0)))
            else: min_down_intervals_remaining_init=0
            #initial up down time
            if min_up_intervals_remaining_init>0: 
                self.add_constraint('minuptime', tInitial, 0==sum([(1-self.status(times[t])) for t in range(min_up_intervals_remaining_init)]))
            if min_down_intervals_remaining_init>0: 
                self.add_constraint('mindowntime', tInitial, 0==sum([self.status(times[t]) for t in range(min_down_intervals_remaining_init)]))


            #initial ramp rate
            if self.rampratemax is not None:
                if self.power(tInitial) + self.rampratemax < self.Pmax:
                    E=self.power(times[0]) - self.intial_power <= self.rampratemax
                    self.add_constraint('ramp lim high', tInitial, E)
                    
            if self.rampratemin is not None:
                if self.power(tInitial) + self.rampratemin > self.Pmin:
                    E=self.rampratemin <= self.power(times[0]) - self.intial_power
                    self.add_constraint('ramp lim low', tInitial, E) 
            
            
            #calculate up down intervals
            min_up_intervals =  roundoff(self.minuptime/times.intervalhrs)
            min_down_intervals = roundoff(self.mindowntime/times.intervalhrs)
        
        for t,time in enumerate(times):
            #bid curve constraints
            self.bid(time).create_constraints()
            #min/max power
            if self.Pmin>0: self.add_constraint('min gen power', time, self.power(time)>=self.status(time)*self.Pmin)
            self.add_constraint('max gen power', time, self.power(time)<=self.status(time)*self.Pmax)
            
            if len(times)==1: continue #if ED or OPF problem
        
            #min up time 
            if t >= min_up_intervals_remaining_init and self.minuptime>0:
                no_shut_down=range(t,min(tEnd,t+min_up_intervals))
                min_up_intervals_remaining=min(tEnd-t,min_up_intervals)
                E = sum([self.status(times[s]) for s in no_shut_down]) >= min_up_intervals_remaining*self.status_change(t,times)
                self.add_constraint('min up time', time, E)
            #min down time        
            if t >= min_down_intervals_remaining_init and self.mindowntime>0:
                no_start_up=range(t,min(tEnd,t+min_down_intervals))
                min_down_intervals_remaining=min(tEnd-t,min_down_intervals)
                E=sum([1-self.status(times[s]) for s in no_start_up]) >= min_down_intervals_remaining * -1 * self.status_change(t,times)
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
                
        
        return
        
    def __str__(self): return 'g{ind}'.format(ind=self.index)
    def __int__(self): return self.index
    def iden(self,t):  return str(self)+str(t)


class Generator_nonControllable(Generator):
    """
    Describes a generator with a fixed schedule.
    The scedule is defined by a :class:`~schedule.Schedule` object.
    """
    def __init__(self,
                 schedule=None,
                 power=None,
                 fuelcost=1,costcurvestring='0',
                 mustrun=False,
                 Pmin=0,Pmax=None,
                 name='',index=None,bus=None,kind='wind',**kwargs):
        update_attributes(self,locals(),exclude=['power']) #load in inputs
        if power is not None and schedule is None: 
            self.schedule = FixedSchedule(P=power)

        if Pmax is None: self.Pmax = self.schedule.maxvalue
        self.is_controllable=False
        self.startupcost=0
        self.shutdowncost=0
        self.build_cost_model()
        self.init_optimization()
    def power(self,time): return self.schedule.get_energy(time)
    def status(self,time): return True
<<<<<<< HEAD
<<<<<<< HEAD
    def set_initial_condition(self,time=None, P=None, u=None, hoursinstatus=None):
        if P is None: P=self.schedule.get_energy(time) #set default power as first scheduled power output
        self.schedule.P[time]=P
<<<<<<< HEAD
    def getstatus(self,t,times): return dict()
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    def add_timevars(self,times): return []
<<<<<<< HEAD
    def update_vars(self,times=None,solution=None): return
=======
    def add_timevars(self,times): return
=======
=======
    def add_timevars(self,times,dispatch_decommit_allowed=False): return []
>>>>>>> initial generator status defaults to off if not specified. solve directory defaults to current directory if not specified. initial conditions spec now accepts ED results.
=======
    def add_timevars(self,times,num_break_points=config.default_num_breakpoints,dispatch_decommit_allowed=False):
        self.build_cost_model(num_break_points)
        return []
>>>>>>> added user breakpoint control by moving buildCostModel into add_timevars
    def update_vars(self,times=None,problem=None): return
>>>>>>> duals and variables now working with coopr. tests are still failing.
    def fix_timevars(self,times=None): return
>>>>>>> added load shedding to insure feasibility
=======
    def create_variables(self,times,num_break_points=config.default_num_breakpoints,dispatch_decommit_allowed=False):
        self.build_cost_model(num_break_points)
        return {}
=======
=======
    def set_initial_condition(self,time=None, P=None, u=None, hoursinstatus=None): pass
>>>>>>> fix for Generator_nonControllable power argument. fix to warning message about generator defaults in makeGenerator
=======
    def set_initial_condition(self,time=None, P=None, u=None, hoursinstatus=None):
        try: 
            if P is None: P=sorted(self.schedule.energy.items())[0][1] #set initial value to first value
            self.schedule.energy[time]=P 
        except AttributeError: pass #fixed schedule
>>>>>>> fix for Generator_nonControllable.set_initial_condition
    def getstatus(self,t,times): return {}
    def create_variables(self,times): return {}
>>>>>>> set all system level parameters as attributes of relevant objects within powersystem init
    def create_constraints(self,times): return {}
>>>>>>> first working pass through solver (results still needs major rework
    def cost(self,time): return self.operatingcost(time)
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    def operatingcost(self,time,sln=None): return self.fuelcost*self.costModel.trueOutput( self.P(time) )
=======
    def operatingcost(self,time): return self.costModel.trueOutput( self.P(time) )
>>>>>>> switched true cost reporting over from bid to cost model
=======
    def operatingcost(self,time): return self.costModel.trueOutput( self.power(time) )
>>>>>>> reformulation of startup,shutdown variables according to Arroyo and Carrion 2006
=======
    def operatingcost(self,time): return self.cost_model.output_true( self.power(time) )
>>>>>>> refactored powersystems. moving on to bidding
    def truecost(self,time): return self.cost(time)
    def incrementalcost(self,time): return self.fuelcost*self.cost_model.output_incremental(self.power(time))

class Load(OptimizationObject):
    """
    Describes a power system load (demand).
    Currently only real power is considered.
    
    :param bus: name of bus that load is on 
      (not required if ED/OPF problem)
    :param schedule: :class:`~schedule.Schedule` object
      (generally created automatically from file
      by :meth:`get_data.build_class_list`)
    :param shedding_allowed: if this load is allowed to be turned off 
    :param cost_shedding: the price of shedding 1MWh of this load
    """
    def __init__(self,kind='varying',name='',index=None,bus=None,schedule=None,
                 shedding_allowed=False,
                 cost_shedding=config.cost_load_shedding
                 ):
        update_attributes(self,locals()) #load in inputs
        self.init_optimization()
    def power(self,time): return self.get_variable('power',time) if self.shedding_allowed else self.schedule.get_energy(time)
    def shed(self,time): return self.schedule.get_energy(time) - self.power(time)
    def cost(self,time): return self.cost_shedding*self.shed(time) 
    def create_variables(self,times):
        if self.shedding_allowed:
            for time in times: self.add_variable('power','Pd',time,low=0,high=self.schedule.get_energy(time))

    def create_objective(self,times):
        return sum([ self.cost(time) for time in times])

    def __str__(self): return 'd{ind}'.format(ind=self.index)    
    def __int__(self): return self.index
    def iden(self,t):     return str(self)+str(t)
    
class Load_Fixed(Load):
    """
    Describes a load that does not vary with time.
    This can be an easy way to add a load for an ED/OPF problem,
    or a system base load.
    
    :param P: real power consumed by load (MW/hr)
    """
    def __init__(self,kind='fixed',name='',index=None,bus=None,P=0,
                 shedding_allowed=False,
                 cost_load_shedding=config.cost_load_shedding
                 ):
        update_attributes(self,locals(),exclude=['p']) #load in inputs
        self.Pfixed = P
        self.init_optimization()
    def shed(self,time): return self.Pfixed- value(self.power(time))
    def power(self,time=None): return self.get_variable('power',time) if self.shedding_allowed else self.Pfixed 
    def create_variables(self,times=None):
        if self.shedding_allowed:
            for time in times: self.add_variable('power','Pd',time,low=0,high=self.Pfixed)
        
class Line(OptimizationObject):
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
        if self.Pmin is None: self.Pmin=-1*self.Pmax #reset default to be -Pmax
        self.init_optimization()
    def power(self,time): return self.get_variable('power',time)
    def price(self,time):
        '''congestion price on line'''
        return dual(self.get_constraint('line flow',time))
    def create_variables(self,times):
        for time in times: self.add_variable('power','P',time)
        return self.all_variables(times)
    def create_constraints(self,times,buses):
        '''create the constraints for a line over all times'''
        for t in times:
            busNames=getattrL(buses,'name')
            iFrom,iTo=busNames.index(self.From),busNames.index(self.To)
            line_flow_ij=self.power(t) == (1/self.X) * (buses[iFrom].angle(t) - buses[iTo].angle(t))
            self.add_constraint('line flow',t,line_flow_ij)
            self.add_constraint('line limit high',t,self.power(t)<=self.Pmax)
            self.add_constraint('line limit low',t,self.Pmin<=self.power(t))
        return 
    def __str__(self): return 'k{ind}'.format(ind=self.index)
    def __int__(self): return self.index
    def iden(self,t): return str(self)+str(t)


class Bus(OptimizationObject):
    """
    Describes a bus (usually a substation where one or more
    tranmission lines start/end).
    
    :param isSwing: flag if the bus is the swing bus 
      (sets the reference angle for the system)
    """
    def __init__(self,name=None,index=None,isSwing=False):
        update_attributes(self,locals()) #load in inputs
        if index is None: self.index=hash(self)
        self.generators,self.loads=[],[]
<<<<<<< HEAD
        #self.angle,self.price=dict(),dict()
        self.init_optimization()
=======
        self.angle,self.price=dict(),dict()
    def add_timevars(self,times):
        for time in times: self.angle[time]=new_variable(name='angle_'+self.iden(time))
        return self.angle.values()
    def update_vars(self,times,problem):
        for time in times: self.angle[time]=value(self.angle[time],problem)
>>>>>>> renamed newVar to new_variable

    def add_timevars(self,times): return self.create_variables(times)
    
<<<<<<< HEAD
    def angle(self,time):
        return self.variables['angle_'+self.iden(time)]
    def price(self,time):
        return self.constraints['powerBalance_'+self.iden(time)].dual
    def create_variables(self,times):
        for time in times: 
            self.add_variable('angle',time)
        return self.variables
        
    def __str__(self):     return 'i{ind}'.format(ind=self.index)
    def iden(self,t):        return str(self)+str(t)
    def Pgen(self,t):   return sumVars([gen.power(t) for gen in self.generators])
    def Pload(self,t):  return sumVars([ ld.power(t) for ld in self.loads])
        
    def constraints(self,times,Bmatrix,buses): return self.create_constraints(times,Bmatrix,buses)
    
    def create_constraints(self,times,Bmatrix,buses):
        '''create the constraints for a bus over all times'''
        def powerBalance(self,t,Bmatrix,allBuses):
            if len(allBuses)==1: lineFlowsFromBus=0
            else: lineFlowsFromBus=sumVars([Bmatrix[self.index][otherBus.index]*otherBus.angle(t) for otherBus in allBuses]) #P_{ij}=sum_{i} B_{ij}*theta_j ???
            return sumVars([ -lineFlowsFromBus,-self.Pload(t),self.Pgen(t) ])
            
=======
    def angle(self,time): return self.get_variable('angle',time)
    def price(self,time): return dual(self.get_constraint('power balance',time))
    def Pgen(self,t):   return sum(gen.power(t) for gen in self.generators)
    def Pload(self,t):  return sum(ld.power(t) for ld in self.loads)
    def power_balance(self,t,Bmatrix,allBuses):
        if len(allBuses)==1: lineFlowsFromBus=0
        else: lineFlowsFromBus=sum([Bmatrix[self.index][otherBus.index]*otherBus.angle(t) for otherBus in allBuses]) #P_{ij}=sum_{i} B_{ij}*theta_j ???
        return sum([ -lineFlowsFromBus,-self.Pload(t),self.Pgen(t) ])
    def create_variables(self,times):
        self.add_children(self.generators,'generators')
        self.add_children(self.loads,'loads')
        logging.debug('added bus {} components - generators and loads {}'.format(self.name,show_clock()))
#        if len(self.generators)<50:
        for gen in self.generators: gen.create_variables(times)             
#        else:
#            for gen in self.generators:
#                threading.Thread(target=_call_generator_create_variables,args=(gen,times)).start()
#            else:
#                for th in threading.enumerate():  
#                    if th is threading.current_thread(): continue
#                    else: th.join()

        logging.debug('created generator variables {}'.format(show_clock()))
        for load in self.loads: load.create_variables(times)
        logging.debug('created load variables {}'.format(show_clock()))
        for time in times: self.add_variable('angle',time=time)
        logging.debug('created bus variables ... returning {}'.format(show_clock()))
        return
    def create_objective(self,times):
        return sum(gen.create_objective(times) for gen in self.generators) + \
            sum(load.create_objective(times) for load in self.loads)
    def create_constraints(self,times,Bmatrix,buses):
        for gen in self.generators: gen.create_constraints(times)
        for load in self.loads: load.create_constraints(times)
>>>>>>> refactored powersystems. moving on to bidding
        nBus=len(buses)
<<<<<<< HEAD
        for t in times:
<<<<<<< HEAD
            iden=self.iden(t)
            if nBus>1 and self.isSwing: constraints['swingBus '+iden] = self.angle[t]==0 #swing bus has angle=0
<<<<<<< HEAD
            logging.debug('added a power balance constraint')
=======
>>>>>>> added status method for Generator() and getprice for bus().
            constraints['powerBalance_'+iden] = powerBalance(self,t,Bmatrix,buses)==0 #power balance must be zero
        return constraints
    def getprice(self,time,problem):
        return problem.dual('powerBalance_'+self.iden(time))
=======
            self.add_constraint('powerBalance',t, powerBalance(self,t,Bmatrix,buses)==0) #power balance must be zero
=======
        for time in times:
            self.add_constraint('power balance',time, self.power_balance(time,Bmatrix,buses)==0) #power balance must be zero
>>>>>>> first working pass through solver (results still needs major rework
            if nBus>1 and self.isSwing: 
<<<<<<< HEAD
                self.add_constraint('swingBus',t, self.angle(t)==0)#swing bus has angle=0
            
        return self.constraints
    def getprice(self,time,problem): return self.price(time)
    
        #return problem.dual('powerBalance_'+self.iden(time))
>>>>>>> this is going to be a major refactor. putting on hold for now.
        


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
<<<<<<< HEAD
<<<<<<< HEAD
    def benifit(self,time=None): return 0
    def add_timevars(self,times=None): return []
=======
    def benifit(self,time=None): return (self.P(time) - self.schedule.getEnergy(time))*config.cost_loadshedding
    def shed(self,time): return self.schedule.getEnergy(time)- value(self.P(time)) #power_to_energy(value(self.P(time)),time)
=======
    def benifit(self,time=None): return (self.power(time) - self.schedule.getEnergy(time))*config.cost_loadshedding
    def shed(self,time): return self.schedule.getEnergy(time)- value(self.power(time)) #power_to_energy(value(self.power(time)),time)
>>>>>>> reformulation of startup,shutdown variables according to Arroyo and Carrion 2006
    def add_timevars(self,times=None,shedding_allowed=False):
        if shedding_allowed: 
            for t in times: self.dispatched_power[t]=new_variable('Pd_{}'.format(self.iden(t)),low=0,high=self.schedule.getEnergy(t))
        else:
            for t in times: self.dispatched_power[t]=self.schedule.getEnergy(t)
        return self.dispatched_power.values()
    
    def update_vars(self,times,problem):
        for t in times: self.dispatched_power[t]=value(self.dispatched_power[t],problem)

<<<<<<< HEAD
    def fix_timevars(self,times=None):
        for t in times: self.dispatched_power[t]=value(self.dispatched_power[t])
>>>>>>> added load shedding to insure feasibility
=======
>>>>>>> changed fix_timevars to fix_vars in Generator(). fixed reporting on load shedding.
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
    


        


=======
                self.add_constraint('swing bus',time, self.angle(time)==0)#swing bus has angle=0
        return
    # def clear_constraints(self):
    #     self.constraints={}
    #     for gen in self.generators: gen.clear_constraints()
    #     for load in self.loads: load.clear_constraints()

    def iden(self,t):   return str(self)+str(t)
    def __str__(self):  return 'i{ind}'.format(ind=self.index)
<<<<<<< HEAD
>>>>>>> refactored powersystems. moving on to bidding
=======
    
<<<<<<< HEAD
>>>>>>> set all system level parameters as attributes of relevant objects within powersystem init
class PowerSystem(OptimizationObject):
=======
class PowerSystem(OptimizationProblem):
>>>>>>> basic conversion of power_system to OptimziationProblem object
    '''
    Power systems object which is the container for all other components.
    
    :param generators: list of :class:`~powersystem.Generator` objects
    :param loads: list of :class:`~powersystem.Load` objects
    :param lines: list of :class:`~powersystem.Line` objects
    :param num_breakpoints: number of break points to use in linearization
      of a generator's bid (or cost) polynomials (equal to number of segments + 1)
    :param load_shedding_allowed: flag - whether load shedding is allowed
    :param cost_load_shedding: price of load shedding [$/MWh]
    :param dispatch_decommit_allowed: flag - if generators can be decommitted during dispatch 
    '''
    def __init__(self,
                 generators,loads,lines=None,
                 num_breakpoints=config.default_num_breakpoints,
                 load_shedding_allowed=False,
                 cost_load_shedding=config.cost_load_shedding,
                 #spinning_reserve_requirement=0,
                 dispatch_decommit_allowed=False,
                 ):
        update_attributes(self,locals(),exclude=['generators','loads','lines']) #load in inputs
        if lines is None: lines=[]    
            
        buses=self.make_buses_list(loads,generators)
        self.create_admittance_matrix(buses,lines)
        self.init_optimization()
        
        self.add_children(buses,'buses')
        self.add_children(lines,'lines')
        
        #add system mode parameters to relevant components
        self.set_load_shedding(load_shedding_allowed) #set load shedding
        for load in loads:
                try: 
                    load.cost_model.num_breakpoints=num_breakpoints
                    load.cost_model.do_segmentation()
                except AttributeError: pass #load has no cost model   
        for gen in generators:
            gen.dispatch_decommit_allowed=dispatch_decommit_allowed
            try: 
                gen.cost_model.num_breakpoints=num_breakpoints
                gen.cost_model.do_segmentation()
            except AttributeError: pass #gen has no cost model
            
    def set_load_shedding(self,is_allowed):
        '''set system mode for load shedding'''
        for load in self.loads():
            load.shedding_allowed=is_allowed 
            load.cost_shedding=self.cost_load_shedding
             
    def make_buses_list(self,loads,generators):
        """
        Create list of :class:`powersystems.Bus` objects 
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
    def create_admittance_matrix(self,buses,lines):
        """
        Creates the admittance matrix (B), 
        with elements = total admittance of line from bus i to j.
        Used in calculating the power balance for OPF problems.
        
        :param buses: list of :class:`~powersystems.Line` objects
        :param lines: list of :class:`~powersystems.Bus` objects
        """
        nB=len(buses)
        self.Bmatrix=numpy.zeros((nB,nB))
        namesL=[bus.name for bus in buses]
        for line in lines:
            busFrom=buses[namesL.index(line.From)]
            busTo=buses[namesL.index(line.To)]
            self.Bmatrix[busFrom.index,busTo.index]+=-1/line.X
            self.Bmatrix[busTo.index,busFrom.index]+=-1/line.X
        for i in range(0,nB): 
            self.Bmatrix[i,i]=-1*sum(self.Bmatrix[i,:])
    def loads(self): return flatten(bus.loads for bus in self.buses)
    def generators(self): return flatten(bus.generators for bus in self.buses)
    def create_variables(self,times):
<<<<<<< HEAD
        self.add_variable('cost first stage','C1')
        self.add_variable('cost second stage','C2')        
=======
        self.add_set('times',[str(t) for t in times])
        times.set=self._model.times
        
>>>>>>> major overahual on setting up variables/constraints directly to the parent problem. this allows the use of sets, variable lists. still need to cleanup (including dual values).
        for bus in self.buses:  bus.create_variables(times)
        for line in self.lines: line.create_variables(times)
        logging.debug('... created power system vars... returning... {}'.format(show_clock()))
        #for var in self.all_variables(times).values(): self.add_variable(var)
        
    def create_objective(self,times):
<<<<<<< HEAD
        #return sum(bus.create_objective(times) for bus in self.buses) + sum(line.create_objective(times) for line in self.lines)
        return self.variables['cost_first_stage_system']+self.variables['cost_second_stage_system']
=======
        obj=sum(bus.create_objective(times) for bus in self.buses) + sum(line.create_objective(times) for line in self.lines)
        self.add_objective(obj)
>>>>>>> basic conversion of power_system to OptimziationProblem object
    def create_constraints(self,times):
        for bus in self.buses: bus.create_constraints(times,self.Bmatrix,self.buses)
        for line in self.lines: line.create_constraints(times,self.buses)
        #a system reserve constraint would go here
<<<<<<< HEAD
<<<<<<< HEAD
        self.add_constraint('system cost first stage',None,expression=self.variables['cost_first_stage_system']==sum(gen.cost_first_stage(times) for gen in self.generators()))
        self.add_constraint('system cost second stage',None,expression=self.variables['cost_second_stage_system']==sum(gen.cost_second_stage(times) for gen in self.generators()))

        return self.all_constraints(times)
    def iden(self,time): return 'system'
=======
        for constraint in self.all_constraints(times).values(): self.add_constraint(constraint)
=======
        #for constraint in self.all_constraints(times).values(): self.add_constraint(constraint)
>>>>>>> major overahual on setting up variables/constraints directly to the parent problem. this allows the use of sets, variable lists. still need to cleanup (including dual values).
    
>>>>>>> basic conversion of power_system to OptimziationProblem object
    
#def power_to_energy(P,time):
#    return P*time.intervalhrs
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    
<<<<<<< HEAD
<<<<<<< HEAD
=======
def filter_optimization_objects(objects,times):
    times_str=[str(t).lstrip('t') for t in times]
    times_str.append(str(times.initialTime).lstrip('t'))
    def valid(name,val):
        in_time_period=name.rsplit('t',1)[1] in times_str
        is_variable_not_fixed = getattr(val,'value',0)==None
        return in_time_period and is_variable_not_fixed
    return dict(filter(lambda (name,val): valid(name,val) ,objects.items()))
>>>>>>> rough optimization object model for generator. unit and integration tested.
=======
>>>>>>> working on the big refactor to opt.obj. model
=======
def _call_generator_create_variables(gen,times): return gen.create_variables(times)
=======
#def _call_generator_create_variables(gen,times): return gen.create_variables(times)
>>>>>>> do_segmentation at update breakpoints in PowerSystem
=======
>>>>>>> merged in changes from DR_model

>>>>>>> debugging times for problem creation
