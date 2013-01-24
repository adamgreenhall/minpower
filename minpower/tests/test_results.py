from test_utils import *
from minpower.results import make_solution

@istest
@with_setup(teardown=reset_config)
def check_power_status():
    '''
    Ensure that the solution generator_status and generator_power attributes
    match with the optimization values returned.
    '''
    generators=[
        make_cheap_gen(pmax=100),
        make_mid_gen(pmax=20),
        make_expensive_gen()
    ]

    user_config.duals = True
    power_system, times = solve_problem(generators, 
        **make_loads_times(Pdt=[80,110,130]))
    
    sln = make_solution(power_system, times)
    t0 = sln.generators_power.index[0]
    
    assert(sln.generators_power.ix[t0, 'g0'] == \
        value(generators[0].power(times[0])) )
        
    assert(sln.generators_status.ix[t0, 'g1'] == \
        value(generators[1].status(times[0])) )
