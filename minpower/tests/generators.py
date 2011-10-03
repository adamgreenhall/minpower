'''Test the constraint behavior of the generators'''

from attest import Tests,Assert
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.powersystems import Generator
from minpower.optimization import value

generation = Tests()
generation_updown_times = Tests()

singletime=schedule.just_one_time()

def make_single_bus(generators,loads):
    singlebus=powersystems.Bus()
    singlebus.generators=generators
    singlebus.loads=loads
    return [singlebus]    

def make_cheap_gen(**kwargs):
    return Generator(name='cheap gen', costcurvestring='10P', **kwargs)
def make_mid_gen(**kwargs):
    return Generator(name='middle-range gen', costcurvestring='20P', **kwargs)    
def make_expensive_gen(**kwargs):
    return Generator(name='expensive gen', costcurvestring='30P', **kwargs)    
def make_load(Pd=200,Pdt=None):
    if Pdt is None: 
        return dict(load=[powersystems.Load_Fixed(P=Pd)],times=singletime)
    else: 
        times = schedule.make_times_basic(N=len(Pdt))
        #logging.critical([unicode(t) for t in times])
        sched = schedule.Schedule(times=times, P=Pdt)
        return dict(load=[powersystems.Load(schedule=sched)],times=times)

def solve_problem(generators,load,  gen_init=None, lines=None, solver=config.optimization_solver):
    if lines is None: lines=[]
    
    times=load['times']
    if len(times)>0: 
        for g,gen in enumerate(generators): 
            if gen_init is None: gen.setInitialCondition(times.initialTime)
            else:                gen.setInitialCondition(times.initialTime, **gen_init[g])
            gen.index=g
        
    buses=make_single_bus(generators,loads=load['load'])
    problem=solve.create_problem(buses,lines,times)
    problem.solve(solver=solver)
    if problem.solved:
        for g in generators: g.fix_vars(times,problem)
    else:
        #logging.critical( [g.power[times.initialTime] for g in generators] )
        problem.write('problem.lp')
        raise optimization.OptimizationError('infeasible problem, wrote to problem.lp')
    return problem,times

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
    problem,times=solve_problem(generators,load,gen_init=initial)
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
    problem,times=solve_problem(generators,load,gen_init=initial)
    assert generators[1].power[times[1]] - generators[1].power[times[0]] == ramp_limit

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
    
    problem,times=solve_problem(generators,load,gen_init=initial)
    ramp_rate = Assert(generators[0].power[times[0]] - generators[0].power[times.initialTime])
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
    problem,times=solve_problem(generators,load,gen_init=initial)
    ramp_rate = Assert(generators[1].power[times[0]] - generators[1].power[times.initialTime])
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
    load = make_load(Pdt=[80,120,80,80])
    problem,times=solve_problem(generators,load,gen_init=initial)
    limgen_status=Assert([generators[1].u[t] for t in times])
    assert limgen_status == [0,1,1,0]

@generation.test
def min_down_time():
    '''
    Create three generators: 
        -cheap with max power limit
        -mid with min down time
        -expensive
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
    problem,times=solve_problem(generators,load,gen_init=initial)
    limgen_status=Assert([generators[1].u[t] for t in times])
    expensive_status_t2 = Assert(generators[2].u[times[2]])
    assert limgen_status==[1,0,0,1] and expensive_status_t2==1

           
if __name__ == "__main__": 
    generation.run()