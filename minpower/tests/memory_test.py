'''Test for memory leaks'''
from attest import Tests
from minpower import optimization,powersystems,schedule,solve,config
from test_utils import solve_problem,make_loads_times,make_cheap_gen,make_mid_gen,make_expensive_gen,gen_costs
from coopr import pyomo


import objgraph

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
    
    test_types = dict(
        variable  = pyomo.Var, 
        piecewise = pyomo.Piecewise,
        )
    
    # use objgraph to make sure they don't 
    test_counts = {}
    for name, kind in test_types.iteritems():
        test_counts[name] = len(objgraph.by_type( kind ))
        
    assert sum(test_counts.values()) == 0

    
if __name__ == "__main__": 
    mem.run()
