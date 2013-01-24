'''Test the constraint behavior of an OPF'''
from minpower import powersystems
from minpower.optimization import value
from minpower.commonscripts import Series

from test_utils import *

def test_config():
    assert(user_config.duals == False)
    
@istest
@with_setup(get_duals)
def line_limit_high():
    '''
    Create a two bus system
        -cheap gen on busA
        -expensive gen and load on busB, 
        -line limit lower than load
    Ensure that: 
        - the line is at its limit 
        - the congestion price is equal to the diff. in LMPs
    '''
    pmax=100
    generators=[
        make_cheap_gen(bus='A'),
        make_expensive_gen(bus='B')
    ]    
    lines=[powersystems.Line(pmax=pmax, frombus='A', tobus='B')]
    power_system,times=solve_problem(generators, lines=lines, **make_loads_times(Pd=225,bus='B'))
    Pline = value(lines[0].power(times[0]))
    lmps = [b.price(times[0]) for b in power_system.buses]
    congestion_price = lines[0].price(times[0])
    assert Pline == pmax and congestion_price == (lmps[1] - lmps[0])

@istest
@with_setup(get_duals)
def line_limit_low():
    '''
    Create a two bus system
        -cheap gen on busA
        -expensive gen and load on busB, 
        -line (from B to A) limit lower than load
    Ensure that: 
        - the line is at its limit 
        - the congestion price is equal to the diff. in LMPs
    '''
    pmin = -100
    generators=[
        make_cheap_gen(bus='A'),
        make_expensive_gen(bus='B')
    ]    
    lines=[powersystems.Line(pmin=pmin, frombus='B', tobus='A')]
    power_system,times=solve_problem(generators,lines=lines, **make_loads_times(Pd=225,bus='B'))
    Pline = lines[0].power(times[0])
    lmps=[b.price(times[0]) for b in power_system.buses]
    congestion_price = lines[0].price(times[0])
    assert Pline==pmin and congestion_price == -1*(lmps[1] - lmps[0])


@istest
@with_setup(get_duals)
def three_buses():
    '''
    Create a three bus system
        -cheap gen and load on busA
        -mid gen and load on busB
        -expensive gen and load on busC
        -three lines connecting all three buses (triangle)
        -create congestion by setting a line limit
    Ensure that: 
        - the total load is met
        - the lmps are different
    '''
    pmax=50
    Pd=[105,225,302]
    generators=[
        make_cheap_gen(bus='A'),
        make_mid_gen(bus='B'),
        make_expensive_gen(bus='C'),
        ]    
    loads=[
        powersystems.Load(schedule=Series(Pd[0],singletime), bus='A'),
        powersystems.Load(schedule=Series(Pd[1],singletime), bus='B'),
        powersystems.Load(schedule=Series(Pd[2],singletime), bus='C')
        ]
    lines=[
        powersystems.Line(frombus='A', tobus='B'),
        powersystems.Line(frombus='A', tobus='C', pmax=pmax),
        powersystems.Line(frombus='B', tobus='C', pmax=pmax),
        ]
    power_system,times=solve_problem(generators,times=singletime,loads=loads,lines=lines)
    num_lmps=len(set(b.price(times[0]) for b in power_system.buses))
    total_load = value(sum(b.Pload(times[0]) for b in power_system.buses))
    assert total_load==sum(Pd) and num_lmps>1

def test_config_cleared():
    assert(user_config.duals == False)
