'''Test the constraint behavior of the generators'''

from attest import Tests,Assert,assert_hook
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.powersystems import Generator
from minpower.optimization import value

from test_utils import solve_problem,make_loads_times,singletime,make_cheap_gen,make_mid_gen,make_expensive_gen

generation = Tests()
test_new = Tests()

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
    power_system,times=solve_problem(generators,**make_loads_times(Pd))
    assert generators[0].power(times[0]) == Pmax
    
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
    power_system,times=solve_problem(generators,**make_loads_times(Pd))
    assert generators[1].power(times[0]) == Pmin

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
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[250,350]))
    print generators[1]._parent_problem()
    assert generators[0].power(times[1]) - generators[0].power(times[0]) == ramp_limit
    
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
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[550,450]))
    ramp_rate = generators[1].power(times[1]) - generators[1].power(times[0])
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
    
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[350,350]))
    ramp_rate = generators[0].power(times[0]) - generators[0].initial_power
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
    
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[300,300]))
    ramp_rate = generators[1].power(times[0]) - generators[1].initial_power
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
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[85,120,80,80]))
    limgen_status=[generators[1].status(t) for t in times]
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
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[150,10,140,140]))
    limgen_status=Assert([generators[1].status(t) for t in times])
    expensive_status_t2 = generators[2].status(times[2])
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
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[80,120]))
    assert generators[1].cost_startup(times[1])==startupcost

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
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[150,10]))
    assert generators[1].cost_shutdown(times[1])==shutdowncost

@generation.test
def min_up_time_longer():
    '''
    Create two generators: cheap with max power limit, exp. with min up time and min power limits.
    Create load that increases over the cheap limit at t1 and then reduces back to constant.
    Ensure that the expensive generator is on at t1 and t2, then turns off. 
    '''
    generators=[
        make_cheap_gen(Pmax=100),
        make_expensive_gen(minuptime=8,Pmin=5)   ]
    initial = [
        dict(P= 80, u=True,hoursinstatus=1),
        dict(u=False,hoursinstatus=0)]
    _,times=solve_problem(generators,gen_init=initial,**make_loads_times(Pdt=[85,120,80,80,70,70,70,70,80,80]))
    limgen_status=[generators[1].status(t) for t in times]
    #logging.critical(limgen_status)
    #logging.critical([(generators[1].startup(t),generators[1].shutdown(t)) for t in times])
    #logging.critical(problem.constraints['minuptime_g1t01'])
    assert limgen_status == [0,1,1,1,1,1,1,1,1,0] or limgen_status == [1,1,1,1,1,1,1,1,0,0]

    
if __name__ == "__main__": 
    generation.run()
