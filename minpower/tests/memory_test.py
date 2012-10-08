'''Test for memory leaks'''
from attest import Tests
from minpower import optimization,powersystems,schedule,solve,config
from test_utils import solve_problem,make_loads_times,make_cheap_gen,make_mid_gen,make_expensive_gen,gen_costs
from coopr import pyomo


import objgraph

def get_counts():
    test_types = dict(
        variable  = pyomo.Var, 
        piecewise = pyomo.Piecewise,
        )
    
    # use objgraph to check if these pyomo objects still exist 
    test_counts = {}
    for name, kind in test_types.iteritems():
        test_counts[name] = len(objgraph.by_type( kind ))

    return test_counts    

mem = Tests()

@mem.test
def leak_on_reset():
    # create a problem
    loads_times = make_loads_times(Pdt=[20,30,40,50])
    generators = [
        powersystems.Generator(name='expensive', costcurvestring='30P+0.01P^2'),
        powersystems.Generator(name='cheap', costcurvestring='20P+0.005P^2')
        ]
    
    # solve it
    power_system, times = solve_problem(generators, **loads_times)
    # reset the model - no pyomo components should persist
    power_system.reset_model()
        
    test_counts = get_counts()    
    assert sum(test_counts.values()) == 0

@mem.test
def leak_on_stochastic_reset():

    solve.solve_problem(datadir='./uc-stochastic',
        shell = False,
        csv = False,
        hours_commitment = 24,
        hours_commitment_overlap = 12,
        get_duals = False,
        Nscenarios = None,
    )   
    
    test_counts = get_counts()    
    assert sum(test_counts.values()) == 0


if __name__ == "__main__": 
    mem.run()
