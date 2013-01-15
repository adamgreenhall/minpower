'''Test the constraint behavior of the generators'''

import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

import pandas as pd
from minpower.generators import Generator, Generator_nonControllable
from minpower.optimization import value
from minpower import results

from test_utils import *


@istest
def power_maximum():
    '''
    Create two generators, one cheap and one expensive. 
    Give the cheap one a maximum power limit lower than the load.
    Ensure that the cheaper unit is at its limit.
    '''
    pmax=100
    Pd=221
    generators=[
        make_cheap_gen(pmax=pmax),
        make_expensive_gen()
        ]
    power_system,times=solve_problem(generators,**make_loads_times(Pd))
    assert generators[0].power(times[0]) == pmax
    
@istest
def power_minimum():
    '''
    Create two generators, one cheap and one expensive, status on for both.
    Give the expensive one a min power limit.
    Ensure that the exp. unit is at its limit.
    '''
    pmin=10
    Pd=221
    generators=[
        make_cheap_gen(),
        make_expensive_gen(pmin=pmin)
        ]
    power_system,times=solve_problem(generators,**make_loads_times(Pd))
    assert generators[1].power(times[0]) == pmin

@istest
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
    initial = [{'power':250},{'power':250}]
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[250,350]))
    print generators[1]._parent_problem()
    assert generators[0].power(times[1]) - generators[0].power(times[0]) == ramp_limit
    
@istest
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
    initial = [{'power':250},{'power':250}]
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[550,450]))
    ramp_rate = value(generators[1].power(times[1])) - value(generators[1].power(times[0]))
    assertAlmostEqual(ramp_rate, ramp_limit)

@istest
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
    initial = [{'power':250},{'power':250}]
    
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[350,350]))
    ramp_rate = generators[0].power(times[0]) - generators[0].initial_power
    assert ramp_rate == ramp_limit


@istest
def ramp_down_initial():
    '''
    Create 2 gen, expensive one with ramp down limit. 
    Create load that ramps down faster than limit, at t0.
    Ensure that exp. unit is at its limit.
    '''
    ramp_limit= -80
    generators = [
        make_cheap_gen(),
        make_expensive_gen(rampratemin=ramp_limit)]
    initial = [{'power':250},{'power':250}]
    
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[300,300]))
    ramp_rate = generators[1].power(times[0]) - generators[1].initial_power
    assert ramp_rate == ramp_limit


@istest
def cold_ramp_up():
    '''
    Create three generators, one that must ramp up from cold. 
    Ensure that the generator ramps at within its limit.
    '''
    ramp_limit_SU = 20
    ramp_limit = 30
    generators = [
        make_cheap_gen(pmax=200),
        make_mid_gen(pmin=10, rampratemax=ramp_limit, 
            startupramplimit=ramp_limit_SU),
        make_expensive_gen(pmin=1)]
    initial = [{'power': 200}, {'status': 0}, {'status': 0}]

    power_system, times = solve_problem(generators, gen_init=initial, 
        **make_loads_times(Pdt=[200, 230, 280]))
    
    ramp_rate_SU = value(generators[1].power(times[1])) - value(generators[1].power(times[0]))
    assert ramp_rate_SU <= ramp_limit_SU
    ramp_rate = value(generators[1].power(times[2])) - value(generators[1].power(times[1]))
    assert ramp_rate <= ramp_limit
    

@istest
def hot_shut_down():
    '''
    Create three generators, one that must shut down from hot. 
    Ensure that the generator ramps within its limit.
    '''
    ramp_limit_SD = -30
    ramp_limit = -20
    generators = [
        make_cheap_gen(pmax=200),
        make_expensive_gen(pmin=20, 
            rampratemin=ramp_limit, 
            shutdownramplimit=ramp_limit_SD
        ),
        make_mid_gen(pmin=1)]
    initial = [{'power': 200}, {'power': 50}, {'power': 50}]

    power_system, times = solve_problem(generators, gen_init=initial, 
        **make_loads_times(Pdt=[280, 150]))
        

    ramp_rate = value(generators[1].power(times[0])) - generators[1].initial_power
    assert ramp_limit <= ramp_rate

    ramp_rate_SD = value(generators[1].power(times[1])) - value(generators[1].power(times[0]))
    assert ramp_limit_SD == ramp_rate_SD 
    assert value(generators[1].status(times[1])) == 0     


@istest
def min_up_time():
    '''
    Create two generators: cheap with max power limit, exp. with min up time and min power limits.
    Create load that increases over the cheap limit at t1 and then reduces back to constant.
    Ensure that the expensive generator is on at t1 and t2, then turns off. 
    '''
    generators=[
        make_cheap_gen(pmax=100),
        make_expensive_gen(minuptime=2,pmin=5)   ]
    initial = [
        dict(power=80, status=True),
        dict(status=False)]
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[85,120,80,80]))
    limgen_status=[generators[1].status(t) for t in times]
    assert limgen_status == [0,1,1,0] or limgen_status == [1,1,0,0]



@istest
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
        make_cheap_gen(pmax=100),
        make_mid_gen(mindowntime=2,pmin=40),
        make_expensive_gen()]
    initial = [
        dict(power=100, status=True),
        dict(power=40, status=True,hoursinstatus=0),
        dict(status=False)]

    _, times = solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[150,10,140,140]))
    limgen_status = [generators[1].status(t) for t in times]
    expensive_status_t2 = generators[2].status(times[2])
    assert limgen_status==[1,0,0,1] and expensive_status_t2==1


@istest
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
        make_cheap_gen(pmax=100),
        make_expensive_gen(pmin=10, startupcost=startupcost)   ]
    initial = [
        dict(power=80, status=True),
        dict(status=False)]
    _, times = solve_problem(generators,
        gen_init=initial,
        **make_loads_times(Pdt=[80,120]))
    assert generators[1].cost_startup(times[1]) == startupcost


@istest
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
        make_cheap_gen(pmax=100),
        make_expensive_gen(shutdowncost=shutdowncost, pmin=20)   ]
    initial = [
        dict(power=80, status=True),
        dict(power=20, status=True)]
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[150,10]))
    assert generators[1].cost_shutdown(times[1])==shutdowncost


@istest
def min_up_time_longer():
    '''
    Create two generators: cheap with max power limit, exp. with min up time and min power limits.
    Create load that increases over the cheap limit at t1 and then reduces back to constant.
    Ensure that the expensive generator is on at t1 and t2, then turns off. 
    '''
    generators=[
        make_cheap_gen(pmax=100),
        make_expensive_gen(minuptime=8,pmin=5)   ]
    initial = [
        dict(power=80, status=True, hoursinstatus=1),
        dict(status=False, hoursinstatus=0)]
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[85,120,80,80,70,70,70,70,80,80]))
    limgen_status=[generators[1].status(t) for t in times]
    #logging.critical(limgen_status)
    #logging.critical([(generators[1].startup(t),generators[1].shutdown(t)) for t in times])
    #logging.critical(problem.constraints['minuptime_g1t01'])
    assert limgen_status == [0,1,1,1,1,1,1,1,1,0] or limgen_status == [1,1,1,1,1,1,1,1,0,0]
    
@istest
def wind_shedding():
    '''
    Create a sheddable wind generator and a situation that requires shedding.
    Ensure that the minimum power is shed.
    '''
    lts = make_loads_times(Pdt=[85, 110, 80, 80])
    Pwind = pd.Series([60, 100, 120, 60], index=lts['times'].strings.values)
    
    generators = [
        Generator_nonControllable(schedule=Pwind, sheddingallowed=True),
        make_expensive_gen()]
    
    power_system, times=solve_problem(generators, **lts)
    assert generators[0].power(times[2]) == 80
    assert generators[0].power(times[3]) == 60
    assert sum(generators[1].power(t).value for t in times) == 25 + 10 + 20
