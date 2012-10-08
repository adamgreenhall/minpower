'''Test for memory leaks'''
from attest import Tests
from minpower import optimization,powersystems,schedule,solve,config
from test_utils import solve_problem,make_loads_times,make_cheap_gen,make_mid_gen,make_expensive_gen,gen_costs
from coopr import pyomo


import objgraph, inspect

def get_counts(prefix=''):
    test_types = [
        'Var', 
        'Piecewise',
        'ScenarioTree',
        'ScenarioTreeNode',
        'Scenario',
        '_SetContainer',
        '_ConstraintArray',
        ]
    
    # use objgraph to check if these pyomo objects still exist 
    objects = {} 
    test_counts = {}
    for name in test_types:
        objects[name] = objgraph.by_type( name )
        test_counts[name] = len(objects[name])
    
    if True:
        for name in test_types:
            if test_counts[name]==0: continue
            else: obj = objects[name][0]
            fname = prefix+'-'+'objgraph-{}-'.format(name)
            objgraph.show_refs( [obj], filename=fname+'refs.png', too_many=50)
            objgraph.show_backrefs([obj], filename=fname+'backref.png')
            objgraph.show_chain(
                objgraph.find_backref_chain( obj, inspect.ismodule),
                filename=fname+'chain.png'
                )
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
        
    test_counts = get_counts('uc')    
    assert sum(test_counts.values()) == 0
    
if __name__ == "__main__": 
    mem.run()
