import config
from config import user_config
from commonscripts import *

from optimization import value,OptimizationObject
from schedule import FixedSchedule, is_init
import bidding


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
        bid_points=None,
        noloadcost=0,
        startupcost=0,shutdowncost=0,
        mustrun=False,
        name='',index=None,bus=None,
        dispatch_decommit_allowed=False):
        
        update_attributes(self,locals()) #load in inputs     
        if self.rampratemin is None and self.rampratemax is not None: self.rampratemin = -1*self.rampratemax
        self.is_controllable=True
        self.commitment_problem=True
        self.build_cost_model()
        self.init_optimization()
        
    def power(self,time=None,scenario=None): 
        '''real power output at time'''
        if time is not None and is_init(time):
            return self.initial_power
        else:
            return self.get_variable('power',time,scenario=scenario,indexed=True)
    
    def power_available(self, time=None, scenario=None):
        '''power availble (constrained by Pmax, ramprate, ...) at time'''
        var_name = 'power_available' if self.commitment_problem else 'power'
        return self.get_variable(var_name,time,scenario=scenario,indexed=True)
    
    def status(self,time=None,scenario=None): 
        '''on/off status at time'''
        if self.commitment_problem: 
            if time is not None and is_init(time):
                return self.initial_status
            else:
                return self.get_variable('status',time,scenario=scenario,indexed=True)
        else: return 1
    def status_change(self,t,times): 
        '''is the unit changing status between t and t-1'''
        if t>0: previous_status=self.status(times[t-1])
        else:   previous_status=self.initial_status        
        return self.status(times[t]) - previous_status
    def power_change(self,t,times):
        '''change in output between power between t and t-1'''
        if t>0: previous_power=self.power(times[t-1])
        else:   previous_power=self.initial_power
        return self.power(times[t])-previous_power
    def cost(self,time,evaluate=False): 
        '''total cost at time (operating + startup + shutdown)'''
        return self.operatingcost(time,evaluate)+self.cost_startup(time,evaluate)+self.cost_shutdown(time,evaluate)
    def cost_startup(self,time,evaluate=False): 
        if self.startupcost==0 or not self.commitment_problem: return 0
        else:
            c=self.get_variable('startupcost',time,indexed=True)
            return c if not evaluate else value(c) 
    def cost_shutdown(self,time,evaluate=False): 
        if self.shutdowncost==0 or not self.commitment_problem: return 0
        else: 
            c=self.get_variable('shutdowncost',time,indexed=True)
            return c if not evaluate else value(c) 
    def operatingcost(self,time=None,evaluate=False): 
        '''cost of real power production at time (based on bid model approximation).'''
        return self.bids.output(time,evaluate)
    def truecost(self,time):
        '''exact cost of real power production at time (based on exact bid polynomial).'''
        return value(self.status(time))*self.bids.output_true(self.power(time))
    def incrementalcost(self,time): 
        '''change in cost with change in power at time (based on exact bid polynomial).'''
        return self.bids.output_incremental(self.power(time)) if value(self.status(time)) else None
    def cost_first_stage(self,times):  return sum(self.cost_startup(time)+self.cost_shutdown(time) for time in times)
    def cost_second_stage(self,times): return sum(self.operatingcost(time) for time in times)
    def getstatus(self,t,times): return dict(u=value(self.status(t)),P=value(self.power(t)),hoursinstatus=self.gethrsinstatus(t,times))
#    def plot_cost_curve(self,P=None,filename=None): self.cost_model.plot(P,filename)
    def gethrsinstatus(self,tm,times, status_var=None):
        if not self.is_controllable: return None
        if status_var is None: status_var = self.status
        
        status=value(status_var(tm))
        
        try: timesClipped=times[:times.index(tm)]
        except: debug(); raise
        try: 
            t_lastchange=(t for t in reversed(timesClipped) if value(status_var(t))!=status ).next()
            return hours(tm.End-t_lastchange.Start)
        except StopIteration: #no changes over whole time period
            h=hours(tm.End-times[0].Start)
            if value(self.initial_status) == status: h+=self.initial_status_hours
            return h
    
    def set_initial_condition(self,time=None, P=None, u=True, hoursinstatus=100):
        '''Set the initial condition at time.'''
        if P is None: P=(self.Pmax-self.Pmin)/2 #set default power as median output
        self.initial_status = bool_to_int(u)
        self.initial_power =  P * self.initial_status #note: this eliminates ambiguity of off status with power non-zero output
        self.initial_status_hours = hoursinstatus
    def build_cost_model(self):
        '''
        parse the coefficients for the polynomial bid curve or point definition
        or setup the paramters
        '''
        bid_params = dict(
            owner=self,
            input_variable=self.power,
            min_input=self.Pmin,
            max_input=self.Pmax,
            status_variable=self.status
            )
        
        if self.bid_points is None:
            # polynomial specification
            self.cost_breakpoints=user_config.breakpoints
            if getattr(self,'heatratestring',None) is not None: 
                self.cost_coeffs=[self.fuelcost*mult for mult in bidding.parse_polynomial(self.heatratestring)]
            else:
                self.cost_coeffs=bidding.parse_polynomial(self.costcurvestring)
            bid_params['polynomial'] = self.cost_coeffs
            bid_params['num_breakpoints'] = self.cost_breakpoints
            if self.noloadcost!=0: raise ValueError('no load cost should be defined as part of the polynomial.')


        else:
            # do some simple validation and delay construction to bidding object 
            min_power_bid = self.bid_points[0][0]
            max_power_bid = self.bid_points[-1][0]
            if min_power_bid>self.Pmin: 
                self.Pmin = min_power_bid
                logging.warning('{g} should have a min. power bid ({mpb}) <= to its min. power limit ({mpl})'.format(g=str(self), mpb=min_power_bid, mpl=self.Pmin))
                
            if max_power_bid<self.Pmax: 
                self.Pmax = max_power_bid
                logging.warning('{g} should have a max. power bid ({mpb}) >= to its max. power limit ({mpl})'.format(g=str(self), mpb=max_power_bid, mpl=self.Pmax))
        
            bid_params['polynomial'] = None
            bid_params['bid_points'] = self.bid_points
            bid_params['constant_term'] = self.noloadcost        

        self.bid_params = bid_params
        

    def create_variables(self,times):
        '''
        Create the optimization variables for a generator over all times. 
        Also create the :class:`bidding.Bid` objects and their variables.
        '''
        self.commitment_problem= len(times)>1 or self.dispatch_decommit_allowed
        self.add_variable('power', index=times.set, low=0, high=self.Pmax)
        if self.commitment_problem:
            self.add_variable('status', index=times.set, kind='Binary',fixed_value=1 if self.mustrun else None)
            #power_available exists for easier reserve requirement
            self.add_variable('power_available',index=times.set, low=0,high=self.Pmax)
            if self.startupcost>0:  self.add_variable('startupcost',index=times.set, low=0,high=self.startupcost)                                                                                                                            
            if self.shutdowncost>0: self.add_variable('shutdowncost',index=times.set, low=0,high=self.shutdowncost)

        self.bids=bidding.Bid(times=times, **self.bid_params)
        return

    def create_objective(self,times):
        return sum(self.cost(time) for time in times)

    def create_constraints(self,times):
        '''create the optimization constraints for a generator over all times'''
        def roundoff(n):
            m=int(n)
            if n!=m: raise ValueError('min up/down times must be integer number of intervals, not {}'.format(n))
            return m
   
        if self.commitment_problem:
            #set initial and final time constraints
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
                self.add_constraint('minuptime', tInitial, 0>=sum([(1-self.status(times[t])) for t in range(min_up_intervals_remaining_init)]))
            if min_down_intervals_remaining_init>0: 
                self.add_constraint('mindowntime', tInitial, 0==sum([self.status(times[t]) for t in range(min_down_intervals_remaining_init)]))


            #initial ramp rate
            if self.rampratemax is not None:
                if self.initial_power + self.rampratemax < self.Pmax:
                    E=self.power(times[0]) - self.initial_power <= self.rampratemax
                    self.add_constraint('ramp lim high', tInitial, E)
            
            if self.rampratemin is not None:
                if self.initial_power + self.rampratemin > self.Pmin:
                    E=self.rampratemin <= self.power(times[0]) - self.initial_power
                    self.add_constraint('ramp lim low', tInitial, E) 
            
            #calculate up down intervals
            min_up_intervals =  roundoff(self.minuptime/times.intervalhrs)
            min_down_intervals = roundoff(self.mindowntime/times.intervalhrs)
        
        for t,time in enumerate(times):
            #min/max power
            if self.Pmin>0: self.add_constraint('min gen power', time, self.power(time)>=self.status(time)*self.Pmin)
            
            self.add_constraint('max gen power', time, self.power_available(time)<=self.status(time)*self.Pmax)
            
            if len(times)==1: continue #if ED or OPF problem
            
            self.add_constraint('max gen power avail', time, self.power(time) <= self.power_available(time) )
            

            #ramping power
            if self.rampratemax is not None:
                self.add_constraint('ramp lim high', time, self.power_available(time) <= self.power(times[t-1]) + self.rampratemax*self.status(times[t-1]) )
            
            if self.rampratemin is not None:
                self.add_constraint('ramp lim low', time,  self.rampratemin <= self.power_change(t,times) )

            
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
                 bid_points=None, noloadcost=0,
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
    def power(self,time): 
        return self.get_parameter('power',time, indexed=True)
    def status(self,time=None,scenarios=None): return True
    def set_initial_condition(self,time=None, P=None, u=None, hoursinstatus=None):
        try: 
            if P is None: P=sorted(self.schedule.energy.items())[0][1] #set initial value to first value
            self.schedule.energy[time]=P 
        except AttributeError: pass #fixed schedule
    def getstatus(self,t,times): return {}
    def create_variables(self,times):
        self.add_parameter('power', index=times.set, values=dict([(str(time), self.get_scheduled_ouput(time)) for time in times]) )
        self.bids=bidding.Bid(
            polynomial=self.cost_coeffs,
            owner=self,
            times=times,
            fixed_input=True
            )
    def create_constraints(self,times): return {}
    def cost(self,time,evaluate=False): return self.operatingcost(time)
    def operatingcost(self,time=None,evaluate=False): return self.bids.output_true( self.power(time) )
    def truecost(self,time): return self.cost(time)
    def incrementalcost(self,time): return self.bids.output_incremental(self.power(time))
    def get_scheduled_ouput(self, time): return float(self.schedule.ix[time])

class Generator_Stochastic(Generator_nonControllable):
    """
    Describes a generator with a stochastic power output.
    """
    def __init__(self,
                 scenario_values=None,
                 fuelcost=1,costcurvestring='0',
                 bid_points=None, noloadcost=0,
                 mustrun=False,
                 Pmin=0,Pmax=None,
                 name='',index=None,bus=None,kind='wind',**kwargs):
        update_attributes(self,locals()) #load in inputs
        self.is_controllable=False
        self.is_stochastic=True
        self.build_cost_model()
        self.init_optimization()
    def power(self,time,scenario=None): return self.get_variable('power',time=time,scenario=scenario,indexed=True)
    
    def _get_scenario_values(self,times,s=0):
        if self.has_scenarios_multistage:
            values = self.scenario_values[times.startdate]
            try: scenario = values.ix[s].values.tolist()
            except: raise KeyError('{} is not an available scenario number'.format(s))
            scenario.pop(0) # dont include the probability
            return [ scenario[t] for t in range(len(times)) ]
        else:
            return [ self.scenario_values[s][time] for time in times ]
    
    def create_variables(self,times):
        self.add_parameter('power', index=times.set, nochecking=True)
        power=self.power(time=None)

        #initialize to first scenario value
        scenario_one = self._get_scenario_values(times, s=0)        
        for t,time in enumerate(times): power[str(time)] = scenario_one[t]
        
        self.bids=bidding.Bid(
            polynomial=self.cost_coeffs,
            owner=self,
            times=times,
            fixed_input=True
            )        
        return
    def cost_startup(self,time): return 0
    def cost_shutdown(self,time): return 0


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
