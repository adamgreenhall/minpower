from pandas import Series, DataFrame
from minpower import powersystems,schedule,solve
from minpower.generators import Generator
from minpower.config import user_config
from minpower.optimization import value, OptimizationError

import nose
from nose.tools import istest, with_setup, raises, set_trace
from nose.tools import eq_ as assert_equal


import logging
logging.basicConfig(
    level=logging.CRITICAL, 
    format='%(levelname)s: %(message)s')



default_config = user_config.copy()

def get_duals():
    user_config.duals = True
    
def reset_config():
    # note - can't set a new user_config, because it would be a local variable
    #   instead, we update it with the defaults
    #   this only works if we aren't adding anything extra to the user_config
    user_config.update(default_config)
    try: assert(user_config == default_config)
    except:
        print DataFrame(dict(
            config=Series(user_config), 
            default=Series(default_config) ))
        raise

singletime=schedule.just_one_time()


gen_costs = dict(cheap=10,mid=20,expensive=30)

def assertAlmostEqual(x,y):
    assert(round(x-y, 5)==0)


#def make_single_bus(generators,loads):
    #singlebus=powersystems.Bus()
    #singlebus.generators=generators
    #singlebus.loads=loads
    #return [singlebus]    

def make_cheap_gen(**kwargs):
    return Generator(name='cheap gen', costcurveequation='{}P'.format(gen_costs['cheap']), **kwargs)
def make_mid_gen(**kwargs):
    return Generator(name='middle-range gen', costcurveequation='{}P'.format(gen_costs['mid']), **kwargs)    
def make_expensive_gen(**kwargs):
    if 'costcurveequation' not in kwargs: kwargs['costcurveequation']='{}P'.format(gen_costs['expensive'])
    return Generator(name='expensive gen', **kwargs)    
def make_loads_times(Pd=200,Pdt=None,**kwargs):
    if Pdt is None:
        times = singletime
        sched = Series(Pd, index=times)
        loads=[powersystems.Load(schedule=sched, **kwargs)]
    else: 
        times = schedule.make_times_basic(N=len(Pdt))
        sched = Series(Pdt, index=times)
        loads=[powersystems.Load(schedule=sched,**kwargs)]
    
    return dict(loads=loads,times=times)

def solve_problem(generators, loads=None, times=None, 
    gen_init=None, lines=None, do_reset_config=True):
    
    if lines is None: lines=[]

    if len(times)>0: 
        for g,gen in enumerate(generators): 
            gen.index=g
            if gen_init is None: gen.set_initial_condition(times.initialTime)
            else:                gen.set_initial_condition(times.initialTime, **gen_init[g])
    
    power_system=powersystems.PowerSystem(generators,loads,lines)
    solve.create_problem(power_system,times)

    try: 
        instance = power_system.solve()
    except OptimizationError:
        #re-do stage, with load shedding allowed
        logging.critical('stage infeasible, re-running with load shedding.')
        power_system.allow_shedding(times)
        try:
            instance = power_system.solve()
        except OptimizationError:
            scheduled, committed = power_system.debug_infeasibe(times)
            set_trace()
            raise OptimizationError('failed to solve, even with load shedding.')
        

    if do_reset_config:
        reset_config()
    
    if power_system.solved:
        power_system.update_variables()
    else:
        #logging.critical( [g.power[times.initialTime] for g in generators] )
        power_system.write_model('problem.lp')
        raise OptimizationError('infeasible problem, wrote to problem.lp')
    return power_system,times
