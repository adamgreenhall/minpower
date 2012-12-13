'''Test the constraint behavior of the bids'''
from minpower.generators import Generator
from minpower.optimization import value

from test_utils import *


@istest
def linear():
    '''
    Create a linear bid curve for one generators.
    Ensure that correct cost is valued for the load.
    '''
    a=5
    b=30
    Pd=221
    generators=[ Generator(costcurvestring='{}+{}P'.format(a,b)) ]
    _,times=solve_problem(generators,**make_loads_times(Pd))
    cost = generators[0].bids.output(times[0], evaluate=True)
    assert cost == a + b*Pd

@istest
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
    generators=[ Generator(costcurvestring='{}+{}P+{}P^2+{}P^3'.format(a,b,c,d)) ]
    _,times=solve_problem(generators,**make_loads_times(Pd))#,problem_filename='bidproblem.lp')
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
    generators=[ Generator(costcurvestring='{}+{}P+{}P^2 - {}P^3'.format(a,b,c,d)) ]
    power_system,times=solve_problem(generators,**make_loads_times(Pd))

    cost = generators[0].bids.output(times[0],evaluate=True) 
    actual_cost = a+ b*Pd+ c*Pd**2 + -1*d*Pd**3
    assert actual_cost <= cost <= 1.05*actual_cost

@istest
def coverage():
    '''
    Make sure that the bid range covers the whole Pmin-Pmax range
    '''
    Pd=221
    a=5
    b=30
    c=.2
    d=.1
    Pmin = 10
    Pmax = 559
    generators=[ Generator(
        costcurvestring='{}+{}P+{}P^2+{}P^3'.format(a,b,c,d), 
        Pmin=Pmin, 
        Pmax=Pmax) ]
    _,times=solve_problem(generators,**make_loads_times(Pd))
    bid_points = generators[0].bids.discrete_input_points
    assert Pmin == bid_points[0] and Pmax == bid_points[-1]


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
        make_cheap_gen(Pmax=80),
        make_mid_gen(Pmax=20),
        make_expensive_gen(
            costcurvestring='{}+{}P+{}P^2'.format(a,b,c),
            mindowntime=1,
            Pmax=50
            )
    ]

    Pdt = [80, 90, 130]

    power_system, times = solve_problem(
        generators, 
        gen_init=[{'P':80}, {'P':0}, {'u':False, 'hoursinstatus':0}],
        **make_loads_times(Pdt=Pdt))
    
    assert(generators[2].cost(times[0], evaluate=True) == 0)
    
if __name__ == '__main__':
    nose.runmodule(argv=[__file__,'-vvs','-x','--pdb', '--pdb-failure'],
                   exit=False)
