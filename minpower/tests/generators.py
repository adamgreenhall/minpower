'''Test the constraint behavior of the generators'''

from attest import Tests,Assert,assert_hook
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.powersystems import Generator
from minpower.optimization import value

from test_utils import *

generation = Tests()


@generation.test
def power_maximum():
    '''
    Create two generators, one cheap and one expensive. 
    Give the cheap one a maximum power limit lower than the load.
    Ensure that the cheaper unit is at its limit.
    '''
    Pmax=100
    Pd=221
    generators=[
        make_cheap_gen(Pmax=Pmax),
        make_expensive_gen()
        ]
    solve_problem(generators,make_load(Pd))
    
    assert generators[0].power[singletime[0]] == Pmax
    
@generation.test
def power_minimum():
    '''
    Create two generators, one cheap and one expensive, status on for both.
    Give the expensive one a min power limit.
    Ensure that the exp. unit is at its limit.
    '''
    Pmin=10
    Pd=221
    generators=[
        make_cheap_gen(),
        make_expensive_gen(Pmin=Pmin)
        ]
    solve_problem(generators,make_load(Pd))
    assert generators[1].power[singletime[0]] == Pmin

@generation.test
def ramp_up():
    '''
    Create 2 gen, cheaper one with ramp up limit. 
    Create load that ramps up faster than limit, at t1.
    Ensure that cheaper unit is at its limit.
    '''
    ramp_limit=80
    generators=[
        make_cheap_gen(rampratemax=ramp_limit),
        make_expensive_gen()
        ]
    initial = [{'P':250},{'P':250}]
    
    load=make_load(Pdt=[250,350])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    assert generators[0].power[times[1]] - generators[0].power[times[0]] == ramp_limit
    
@generation.test
def ramp_down():
    '''
    Create 2 gen, expensive one with ramp down limit. 
    Create load that ramps down faster than limit at t1.
    Ensure that exp. unit is at its limit.
    '''    
    ramp_limit= -80
    generators=[
        make_cheap_gen(),
        make_expensive_gen(rampratemin=ramp_limit)
        ]
    initial = [{'P':250},{'P':250}]
    
    load=make_load(Pdt=[550,450])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    ramp_rate = generators[1].power[times[1]] - generators[1].power[times[0]]
    assert ramp_rate == ramp_limit

@generation.test
def ramp_up_initial():
    '''
    Create 2 gen, cheaper one with ramp up limit. 
    Create load that ramps up faster than limit, at t0.
    Ensure that cheaper unit is at its limit.
    '''
    ramp_limit=80
    generators=[
        make_cheap_gen(rampratemax=ramp_limit),
        make_expensive_gen()
        ]
    initial = [{'P':250},{'P':250}]

    load=make_load(Pdt=[350,350])
    
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    ramp_rate = generators[0].power[times[0]] - generators[0].power[times.initialTime]
    assert ramp_rate == ramp_limit


@generation.test
def ramp_down_initial():
    '''
    Create 2 gen, expensive one with ramp down limit. 
    Create load that ramps down faster than limit, at t0.
    Ensure that exp. unit is at its limit.
    '''
    ramp_limit= -80
    generators=[
        make_cheap_gen(),
        make_expensive_gen(rampratemin=ramp_limit)  ]
    initial = [{'P':250},{'P':250}]
    
    load=make_load(Pdt=[300,300])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    ramp_rate = generators[1].power[times[0]] - generators[1].power[times.initialTime]
    assert ramp_rate == ramp_limit



@generation.test
def min_up_time():
    '''
    Create two generators: cheap with max power limit, exp. with min up time and min power limits.
    Create load that increases over the cheap limit at t1 and then reduces back to constant.
    Ensure that the expensive generator is on at t1 and t2, then turns off. 
    '''
    generators=[
        make_cheap_gen(Pmax=100),
        make_expensive_gen(minuptime=2,Pmin=5)   ]
    initial = [
        dict(P= 80, u=True),
        dict(u=False)]
    load = make_load(Pdt=[85,120,80,80])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    limgen_status=[generators[1].u[t] for t in times]
    assert limgen_status == [0,1,1,0] or limgen_status == [1,1,0,0]

@generation.test
def min_down_time():
    '''
    Create three generators: 
    * cheap with max power limit
    * with min down time
    * expensive
    Create load that is higher than the cheap limit all but t1.
    Ensure that the mid generator is OFF at t1 and t2, then turns on again.
    Ensure that the hi generator is ON for t2 to make up the difference.
    '''
    generators=[
        make_cheap_gen(Pmax=100),
        make_mid_gen(mindowntime=2,Pmin=40),
        make_expensive_gen()]
    initial = [
        dict(P= 100, u=True),
        dict(P=40, u=True,hoursinstatus=0),
        dict(u=False)]
    load = make_load(Pdt=[150,10,140,140])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    limgen_status=Assert([generators[1].u[t] for t in times])
    expensive_status_t2 = generators[2].u[times[2]]
    assert limgen_status==[1,0,0,1] and expensive_status_t2==1


@generation.test
def start_up_cost():
    '''
    Create two generators:
    * cheap with a max power
    * expensive with a start up cost.
    Create an increasing load.
    Ensure that the objective includes the startup cost.
    '''
    startupcost=9000
    generators=[
        make_cheap_gen(Pmax=100),
        make_expensive_gen(startupcost=startupcost)   ]
    initial = [
        dict(P= 80, u=True),
        dict(u=False)]
    load = make_load(Pdt=[80,120])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    obj_startupcost = problem.objective - sum( gen.operatingcost(t) for t in times for gen in generators)
    assert obj_startupcost==startupcost

@generation.test
def shut_down_cost():
    '''
    Create two generators, both on:
    * cheap with a max power
    * expensive with a start down cost and a min power.
    Create an decreasing load.
    Ensure that the objective includes the shutdown cost.
    '''
    shutdowncost=200
    generators=[
        make_cheap_gen(Pmax=100),
        make_expensive_gen(shutdowncost=shutdowncost, Pmin=20)   ]
    initial = [
        dict(P= 80, u=True),
        dict(P=20,u=True)]
    load = make_load(Pdt=[150,10])
    problem,times,buses=solve_problem(generators,load,gen_init=initial)
    obj_sdcost = problem.objective - sum( gen.operatingcost(t) for t in times for gen in generators)
    assert obj_sdcost==shutdowncost

    
if __name__ == "__main__": 
    generation.run()
