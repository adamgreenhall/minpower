'''Test for memory leaks'''
from minpower import powersystems, solve
from test_utils import solve_problem, make_loads_times
from coopr import pyomo


import objgraph, inspect

def show_memory_backrefs(name):    
    objgraph.show_backrefs(
        objgraph.by_type(name),
        filename='backrefs-{}.png'.format(name))


def show_memory_refs(name):
    try: obj=objgraph.by_type(name)[0]
    except IndexError:
        print 'no object of type',name  
        return
    objgraph.show_chain(
        objgraph.find_backref_chain(obj, inspect.ismodule),
        filename='chain-{}.png'.format(name))


def show_memory_growth():
    objgraph.show_growth()

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
            objgraph.show_refs( [obj], filename=fname+'refs.png') # too_many=50,
            objgraph.show_backrefs([obj], filename=fname+'backref.png')
            objgraph.show_chain(
                objgraph.find_backref_chain( obj, inspect.ismodule),
                filename=fname+'chain.png'
                )
    return test_counts    

def leak_on_reset():
    # create a problem
    loads_times = make_loads_times(Pdt=[20,30,40,50])
    generators = [
        powersystems.Generator(name='expensive', costcurveequation='30P+0.01P^2'),
        powersystems.Generator(name='cheap', costcurveequation='20P+0.005P^2')
        ]
    
    # solve it
    power_system, times = solve_problem(generators, **loads_times)
    # reset the model - no pyomo components should persist
    power_system.reset_model()
        
    test_counts = get_counts('uc')    
    assert sum(test_counts.values()) == 0

def leak_on_stochastic_reset():

    solve.solve_problem(datadir='./uc-stochastic',
        shell = False,
        csv = False,
        hours_commitment = 24,
        hours_commitment_overlap = 12,
        get_duals = False,
        Nscenarios = None,
    )   
    
    test_counts = get_counts('uc-stochastic')    
    assert sum(test_counts.values()) == 0


if __name__ == "__main__": 
    leak_on_reset()
