'''Test the higher level behavior of the unit commitment'''
import random
from minpower.generators import Generator
from test_utils import *

@istest
@with_setup(setup=get_duals, teardown=reset_config)
def prices():
    '''
    Run a basic unit commitment. 
    Ensure that the correct LMPs are returned for all times.
    '''
    generators=[
        make_cheap_gen(pmax=100),
        make_mid_gen(pmax=20),
        make_expensive_gen()
    ]

    power_system, times = solve_problem(generators, 
        **make_loads_times(Pdt=[80,110,130]))
    lmps = [power_system.buses[0].price(t) for t in times]
    
    assert lmps==[gen_costs['cheap'],gen_costs['mid'],gen_costs['expensive']]
        
@istest
def rolling():
    '''
    Run a basic unit commitment over 72hrs
    Ensure that the generation meets the load for each time.
    '''
    generators=[Generator(costcurveequation='10P+.01P^2')]
    Pdt=[random.randrange(0, 200) for i in range(0,72)]
    power_system,times=solve_problem(generators,**make_loads_times(Pdt=Pdt))
    load=power_system.loads()[0]
    load_balanced = all(generators[0].power(t)==load.power(t) for t in times)
    assert load_balanced


@istest
@with_setup(teardown=reset_config)
def load_shedding():
    '''
    Create a single generator with a high limit.
    Create a load that exceeds that limit at t1.
    Ensure that:
    * Pdt1=Pgmax
    * Pshedt1 = Pdt1 - pmax
    * pricet1 = cost of load shedding
    '''
    
    user_config.duals = True
    pmax=100
    Pdt1=211
    generators=[make_cheap_gen(pmax=pmax)]
    Pdt=[110,Pdt1,110]
    power_system, times = solve_problem(
        generators, **make_loads_times(Pdt=Pdt))
    load=power_system.loads()[0]
    load_t1=load.power(times[1], evaluate=True)
    load_t1_shed=load.shed(times[1], evaluate=True)
    price_t1 = power_system.buses[0].price(times[1])
    assert load_t1==pmax 
    assert load_t1_shed==Pdt1-pmax
    assert price_t1 == user_config.cost_load_shedding



@istest
@with_setup(teardown=reset_config)
def reserve_fixed_amount():
    '''
    Create two generators, the cheaper one with a limit near the load.
    Require 50MW of reserve (which exceeds pmax of cheap)
    Ensure that: g2 is turned on to meet reserve req.

    Pg1+Pg2 = load
    Pavail1 + Pavail2 = load + reserve
    '''
    reserve_req = 30.0
    user_config.reserve_fixed = reserve_req
    
    generators=[
        make_cheap_gen(pmax=100), 
        make_expensive_gen(pmin=0, pmax=300, costcurveequation='5000+30P')]
    Pdt=[80, 90]    
        
    power_system, times = solve_problem(generators, 
        **make_loads_times(Pdt=Pdt))
    total_power = [sum([value(gen.power(time)) for gen in generators]) for time in times]
    total_available_power = [sum(value(gen.power_available(time)) 
        for gen in generators) for time in times]
        
#    print load_t1 + reserve_req
#    print [[value(gen.power(time)) for gen in generators] for time in times]
#    print total_available_power
#    print [reserve_req + Pd for Pd in Pdt]
    
    assert Pdt == total_power
    assert total_available_power >= [reserve_req + Pd for Pd in Pdt]
