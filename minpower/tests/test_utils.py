from minpower import optimization,powersystems,schedule,solve,config
from minpower.powersystems import Generator

singletime=schedule.just_one_time()


gen_costs = dict(cheap=10,mid=20,expensive=30)


#def make_single_bus(generators,loads):
    #singlebus=powersystems.Bus()
    #singlebus.generators=generators
    #singlebus.loads=loads
    #return [singlebus]    

def make_cheap_gen(**kwargs):
    return Generator(name='cheap gen', costcurvestring='{}P'.format(gen_costs['cheap']), **kwargs)
def make_mid_gen(**kwargs):
    return Generator(name='middle-range gen', costcurvestring='{}P'.format(gen_costs['mid']), **kwargs)    
def make_expensive_gen(**kwargs):
    return Generator(name='expensive gen', costcurvestring='{}P'.format(gen_costs['expensive']), **kwargs)    
def make_loads_times(Pd=200,Pdt=None,**kwargs):
    if Pdt is None:
        loads=[powersystems.Load_Fixed(P=Pd,**kwargs)]
        times=singletime
    else: 
        times = schedule.make_times_basic(N=len(Pdt))
        #logging.critical([unicode(t) for t in times])
        sched = schedule.Schedule(times=times, P=Pdt)
        loads=[powersystems.Load(schedule=sched,**kwargs)]
    
    return dict(loads=loads,times=times)

def solve_problem(generators,loads=None,times=None, gen_init=None, lines=None, 
                  solver=config.optimization_solver,load_shedding_allowed=False,problem_filename=False,
                  get_duals=False
                  ):
    if lines is None: lines=[]

    if len(times)>0: 
        for g,gen in enumerate(generators): 
            gen.index=g
            if gen_init is None: gen.set_initial_condition(times.initialTime)
            else:                gen.set_initial_condition(times.initialTime, **gen_init[g])
            
    
    
    power_system=powersystems.PowerSystem(generators,loads,lines,load_shedding_allowed=load_shedding_allowed)
    solve.create_problem(power_system,times)
    power_system.solve(solver=solver,problem_filename=problem_filename,get_duals=get_duals)
    if power_system.solved:
        power_system.update_variables()
    else:
        #logging.critical( [g.power[times.initialTime] for g in generators] )
        power_system.write_model('problem.lp')
        raise optimization.OptimizationError('infeasible problem, wrote to problem.lp')
    return power_system,times