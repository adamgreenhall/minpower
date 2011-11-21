"""
Defines models for power systems components, including 
:class:`~powersystems.PowerSystem`, :class:`~powersystems.Bus`, 
:class:`~powersystems.Generator`, :class:`~powersystems.Load`,
and  :class:`~powersystems.Line`. Each of these objects inherits
an optimization framework from :class:`~optimization.OptimizationObject`.
"""

from optimization import value,dual,sum_vars,OptimizationObject
from commonscripts import hours,drop_case_spaces,flatten,getattrL,unique,update_attributes,show_clock
import config, bidding
from schedule import FixedSchedule
import logging
#import threading
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
        return self.get_variable('power',time)
    def status(self,time): 
        '''on/off status at time'''
        return self.get_variable('status',time)
    def status_change(self,t,times): 
        '''is the unit changing status between t and t-1'''
        if t>0: previous_status=self.status(times[t-1])
        else:   previous_status=self.status(times.initialTime)
        return self.status(times[t]) - previous_status
    def power_change(self,t,times):
        '''change in output between power between t and t-1'''
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
        return self.bid(time).output()
    def truecost(self,time):
        '''exact cost of real power production at time (based on exact bid polynomial).'''
        return value(self.status(time))*self.cost_model.output_true(self.power(time))
    def incrementalcost(self,time): 
        '''change in cost with change in power at time (based on exact bid polynomial).'''
        return self.bid(time).output_incremental(self.power(time)) if value(self.status(time)) else None
    def bid(self,time):
        ''':class:`~bidding.Bid` object for time'''
        try: return self.get_component('bid', time)
        except KeyError:
            print str(time)
            print self.children
            print [str(c) for c in self.children]
            raise 
    def getstatus(self,t,times): return dict(u=value(self.status(t)),P=value(self.power(t)),hoursinstatus=self.gethrsinstatus(t,times))
    def plot_cost_curve(self,P=None,filename=None): self.cost_model.plot(P,filename)
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
    
    def set_initial_condition(self,time=None, P=None, u=True, hoursinstatus=100):
        '''Set the initial condition at time.'''
        if P is None: P=(self.Pmax-self.Pmin)/2 #set default power as median output
        self.add_variable('status', 'u', time, fixed_value=u)
        self.add_variable('power', 'P', time, fixed_value=P*u) #note: this eliminates ambiguity of off status with power non-zero output
        self.initialStatusHours = hoursinstatus
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
            bid=bidding.Bid(
                    model=self.cost_model,
                    time=time,
                    input_var=self.power(time),
                    status_var=self.status(time),
                    owner_iden=str(self),
                    time_iden=str(time))
            bid.create_variables()
            self.add_component(bid,'bid',time)
        
        #logging.debug('created {} variables {}'.format(str(self),show_clock()))
        return self.all_variables(times)
    def create_objective(self,times):
        self.objective=sum_vars(self.cost(time) for time in times)
        return self.objective

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
                up_intervals_remaining=roundoff((self.minuptime - self.initialStatusHours)/times.intervalhrs)
                min_up_intervals_remaining_init =   int(min(tEnd, up_intervals_remaining*self.status(tInitial) ))
            else: min_up_intervals_remaining_init=0
            if self.mindowntime>0:
                down_intervals_remaining=roundoff((self.mindowntime - self.initialStatusHours)/times.intervalhrs)
                min_down_intervals_remaining_init = int(min(tEnd,down_intervals_remaining*(self.status(tInitial)==0)))
            else: min_down_intervals_remaining_init=0
            #initial up down time
            if min_up_intervals_remaining_init>0: 
                self.add_constraint('minuptime', tInitial, 0==sum_vars([(1-self.status(times[t])) for t in range(min_up_intervals_remaining_init)]))
            if min_down_intervals_remaining_init>0: 
                self.add_constraint('mindowntime', tInitial, 0==sum_vars([self.status(times[t]) for t in range(min_down_intervals_remaining_init)]))


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
            #bid curve constraints
            self.get_component('bid', time).create_constraints()
            #min/max power
            if self.Pmin>0: self.add_constraint('min gen power', time, self.power(time)>=self.status(time)*self.Pmin)
            self.add_constraint('max gen power', time, self.power(time)<=self.status(time)*self.Pmax)
            
            if len(times)==1: continue #if ED or OPF problem
        
            #min up time 
            if t >= min_up_intervals_remaining_init and self.minuptime>0:
                no_shut_down=range(t,min(tEnd,t+min_up_intervals))
                min_up_intervals_remaining=min(tEnd-t,min_up_intervals)
                E = sum_vars([self.status(times[s]) for s in no_shut_down]) >= min_up_intervals_remaining*self.status_change(t,times)
                self.add_constraint('min up time', time, E)
            #min down time        
            if t >= min_down_intervals_remaining_init and self.mindowntime>0:
                no_start_up=range(t,min(tEnd,t+min_down_intervals))
                min_down_intervals_remaining=min(tEnd-t,min_down_intervals)
                E=sum_vars([1-self.status(times[s]) for s in no_start_up]) >= min_down_intervals_remaining * -1 * self.status_change(t,times)
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
                
        
        return self.all_constraints(times)        
        
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
        self.build_cost_model()
        self.init_optimization()
    def power(self,time): return self.schedule.get_energy(time)
    def status(self,time): return True
    def set_initial_condition(self,time=None, P=None, u=None, hoursinstatus=None):
        try: 
            if P is None: P=sorted(self.schedule.P.items())[0][1] #set initial value to first value
            self.schedule.P[time]=P 
        except AttributeError: pass #fixed schedule
    def getstatus(self,t,times): return {}
    def create_variables(self,times): return {}
    def create_constraints(self,times): return {}
    def cost(self,time): return self.operatingcost(time)
    def operatingcost(self,time): return self.cost_model.output_true( self.power(time) )
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
    def shed(self,time): return self.schedule.get_energy(time) - self.power(time) #power_to_energy(value(self.power(time)),time)
    def cost(self,time): return self.cost_shedding*self.shed(time) 
    def create_variables(self,times):
        if self.shedding_allowed:
            for time in times: self.add_variable('power','Pd',time,low=0,high=self.schedule.get_energy(time))

    def create_objective(self,times):
        self.objective=sum_vars([ self.cost(time) for time in times])
        return self.objective

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
        return self.all_constraints(times)
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
        self.generators,self.loads=[],[]
        self.init_optimization()
    
    def angle(self,time): return self.get_variable('angle',time)
    def price(self,time): return dual(self.get_constraint('power balance',time))
    def Pgen(self,t):   return sum_vars([gen.power(t) for gen in self.generators])
    def Pload(self,t):  return sum_vars([ ld.power(t) for ld in self.loads])
    def power_balance(self,t,Bmatrix,allBuses):
        if len(allBuses)==1: lineFlowsFromBus=0
        else: lineFlowsFromBus=sum_vars([Bmatrix[self.index][otherBus.index]*otherBus.angle(t) for otherBus in allBuses]) #P_{ij}=sum_{i} B_{ij}*theta_j ???
        return sum_vars([ -lineFlowsFromBus,-self.Pload(t),self.Pgen(t) ])
    def create_variables(self,times):
        self.add_components(self.generators,'generators')
        self.add_components(self.loads,'loads')
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
        return self.all_variables(times)
    def create_objective(self,times):
        self.objective= \
            sum_vars(gen.create_objective(times) for gen in self.generators) + \
            sum_vars(load.create_objective(times) for load in self.loads)
        return self.objective
    def create_constraints(self,times,Bmatrix,buses):
        for gen in self.generators: gen.create_constraints(times)
        for load in self.loads: load.create_constraints(times)
        nBus=len(buses)
        for time in times:
            self.add_constraint('power balance',time, self.power_balance(time,Bmatrix,buses)==0) #power balance must be zero
            if nBus>1 and self.isSwing: 
                self.add_constraint('swing bus',time, self.angle(time)==0)#swing bus has angle=0
        return self.all_constraints(times)
    # def clear_constraints(self):
    #     self.constraints={}
    #     for gen in self.generators: gen.clear_constraints()
    #     for load in self.loads: load.clear_constraints()

    def iden(self,t):   return str(self)+str(t)
    def __str__(self):  return 'i{ind}'.format(ind=self.index)
    
class PowerSystem(OptimizationObject):
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
        
        self.add_components(buses,'buses')
        self.add_components(lines,'lines')
        
        #add system mode parameters to relevant components
        self.set_load_shedding(load_shedding_allowed) #set load shedding
        for load in loads:
                try: load.cost_model.num_breakpoints=num_breakpoints
                except AttributeError: pass #load has no cost model   
        for gen in generators:
            gen.dispatch_decommit_allowed=dispatch_decommit_allowed
            try: 
                gen.cost_model.num_breakpoints=num_breakpoints
                gen.cost_model.do_segmentation()
            except AttributeError: pass #gen has no cost model
            
    def set_load_shedding(self,is_allowed):
        '''set system mode for load shedding'''
        for bus in self.buses:
            for load in bus.loads:
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
        for bus in self.buses:  bus.create_variables(times)
        for line in self.lines: line.create_variables(times)
        logging.debug('... created power system vars... returning... {}'.format(show_clock()))
        return self.all_variables(times)
    def create_objective(self,times):
        self.objective=sum_vars(bus.create_objective(times) for bus in self.buses) + sum_vars(line.create_objective(times) for line in self.lines)
        return self.objective
    def create_constraints(self,times):
        for bus in self.buses: bus.create_constraints(times,self.Bmatrix,self.buses)
        for line in self.lines: line.create_constraints(times,self.buses)
        #a system reserve constraint would go here
        return self.all_constraints(times)
    # def clear_constraints(self):
    #     self.constraints={}
    #     for bus in self.buses: bus.clear_constraints()
    #     for line in self.lines: line.clear_constraints()
    
    
#def power_to_energy(P,time):
#    return P*time.intervalhrs
#def _call_generator_create_variables(gen,times): return gen.create_variables(times)

