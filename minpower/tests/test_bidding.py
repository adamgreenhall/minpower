'''Test the constraint behavior of the bids'''
import nose
import pandas as pd
import numpy as np
from pandas.util.testing import assert_almost_equal

from minpower.config import user_config
from minpower.generators import Generator
from minpower.optimization import (value, 
    OptimizationProblem, OptimizationObject)
from minpower.bidding import parse_polynomial, TwoVarPW
from test_utils import (istest, with_setup, make_loads_times, solve_problem,
    reset_config, set_trace, make_cheap_gen, make_expensive_gen, make_mid_gen)


@istest
def parser():
    assert parse_polynomial('7x^2 + 6x - 5') == [-5, 6, 7]
    # with explicit * symbol for multiplication
    assert parse_polynomial('7*x^2 + 6 * x - 5') == [-5, 6, 7]
    # random order
    assert parse_polynomial('6*P - 5 + 7*P^2') == [-5, 6, 7]
    # make sure we can skip the linear term
    assert parse_polynomial('6P') == [0, 6]


@istest
def linear():
    '''
    Create a linear bid curve for one generators.
    Ensure that correct cost is valued for the load.
    '''
    a=5
    b=30
    Pd=221
    generators=[ Generator(costcurveequation='{}+{}P'.format(a,b)) ]
    _,times=solve_problem(generators,**make_loads_times(Pd))
    cost = generators[0].bids.output(times[0], evaluate=True)
    assert cost == a + b*Pd

@istest
@with_setup(teardown=reset_config)
def cubic_convex():
    '''
    Create a cubic, convex bid curve for one generators.
    Ensure that linearized cost is within +5% of the true cost
    '''
    Pd=221
    a=5
    b=30
    c=.2
    d=.1
    user_config.breakpoints = 10
    
    generators=[ Generator(costcurveequation='{}+{}P+{}P^2+{}P^3'.format(a,b,c,d)) ]
    power_system, times = solve_problem(
        generators,**make_loads_times(Pd))
    cost = value(generators[0].bids.output(times[0], evaluate=True))
    actual_cost = a+ b*Pd+ c*Pd**2 + d*Pd**3
    assert actual_cost <= cost and cost <= 1.05*actual_cost


@istest
def cubic_non_convex():
    '''
    Create a cubic, but non-convex (negative cubic term) bid curve for one generators.
    Ensure that linearized cost is within +5% of the true cost
    '''
    Pd=221
    a=5
    b=30
    c=.2
    d=.0001
    generators=[ Generator(costcurveequation='{}+{}P+{}P^2 - {}P^3'.format(a,b,c,d)) ]
    power_system,times=solve_problem(generators,**make_loads_times(Pd))

    cost = generators[0].bids.output(times[0],evaluate=True) 
    actual_cost = a+ b*Pd+ c*Pd**2 + -1*d*Pd**3
    assert actual_cost <= cost <= 1.05*actual_cost

@istest
def coverage():
    '''
    Make sure that the bid range covers the whole pmin-pmax range
    '''
    Pd=221
    a=5
    b=30
    c=.2
    d=.1
    pmin = 10
    pmax = 559
    generators=[ Generator(
        costcurveequation='{}+{}P+{}P^2+{}P^3'.format(a,b,c,d), 
        pmin=pmin, 
        pmax=pmax) ]
    _,times=solve_problem(generators,**make_loads_times(Pd))
    bid_points = generators[0].bids.discrete_input_points
    assert pmin == bid_points[0] and pmax == bid_points[-1]


@istest
def fixed_costs_when_off():
    '''
    ensure that generator with fixed cost 
    only charges fixed cost when on
    '''
    a = 5
    b = 30
    c = 0.2
    
    generators=[
        make_cheap_gen(pmax=80),
        make_mid_gen(pmax=20),
        make_expensive_gen(
            costcurveequation='{}+{}P+{}P^2'.format(a,b,c),
            mindowntime=1,
            pmax=50
            )
    ]

    Pdt = [80, 90, 130]

    power_system, times = solve_problem(
        generators, 
        gen_init=[
            {'power': 80}, 
            {'power': 0}, 
            {'status': False, 'hoursinstatus': 0}],
        **make_loads_times(Pdt=Pdt))
    
    assert(generators[2].cost(times[0], evaluate=True) == 0)
    
    
@istest
def two_var_pw():
    '''
    create a simple PW linear function of two variables. 
    ensure that the modeled values are close to the true values.
    '''
    def f(x, y): 
        return x**2 * y**2

    # user_config.debugger = True
    
    Nbreakpoints = 10
    xmin = 2
    xmax = 2.5
    ymin = 2.8
    ymax = 4.5

    model = OptimizationProblem()
    gen = OptimizationObject()
    gen.index = 0
    gen.__str__ = lambda obj: 'gen'
     
    model.add_children([gen], 'gens')
    times = ['t00']
    model.add_set('times', times)
    x = gen.add_variable('x', index=times, low=xmin, high=xmax)
    y = gen.add_variable('y', index=times, low=ymin, high=ymax)
    cost = gen.add_variable('cost', index=times, low=0)
    model.add_objective(sum(cost[t] for t in times))
    
    fcurve = dict(
            inputA=lambda t: x[t],
            inputB=lambda t: y[t],
            output_var=lambda t: cost[t],
            pointsA=np.linspace(xmin - 0.5, xmax + 0.5, Nbreakpoints),
            pointsB=np.linspace(ymin - 0.5, ymax + 0.5, Nbreakpoints),
            output_name='cost',
            owner=gen,
            times=times,
            )
    index = pd.MultiIndex.from_arrays([
        np.repeat(fcurve['pointsA'], len(fcurve['pointsB'])),
        np.tile(fcurve['pointsB'], len(fcurve['pointsA']))],
        names=['pointsA', 'pointsB'])            
    fcurve['pointsOut'] = pd.Series([f(a, b) for a, b in index], index=index)

    gen.fcurve = TwoVarPW(**fcurve)
    
    instance = model.solve()
    
    xVal = x[times[0]].value
    yVal = y[times[0]].value
        
    # make sure the correct minimum values were found
    assert_almost_equal(xVal, xmin)
    assert_almost_equal(yVal, ymin)
    
    # make sure the linearized objective value is
    # within 5% of the true solution
    trueVal = f(xVal, yVal)
    estmVal = float(instance.objective)
    assert(np.abs(estmVal - trueVal) / trueVal < 0.05)
     
if __name__ == '__main__':
    nose.runmodule(argv=[__file__,'-vvs','-x','--pdb', '--pdb-failure'],
                   exit=False)
