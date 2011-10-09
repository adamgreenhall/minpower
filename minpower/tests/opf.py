'''Test the constraint behavior of an OPF'''

from attest import Tests,Assert,assert_hook
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.optimization import value

from test_utils import *

opf = Tests()

@opf.test
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
    Pmax=100
    generators=[
        make_cheap_gen(bus='A'),
        make_expensive_gen(bus='B')
    ]    
    load=make_load(Pd=225,bus='B')
    lines=[powersystems.Line(Pmax=Pmax, From='A',To='B')]
    problem,times,buses=solve_problem(generators,load,lines=lines)
    Pline = lines[0].P[times[0]]
    lmps=[b.getprice(times[0], problem) for b in buses]
    congestion_price = lines[0].getprice(times[0],problem)
    #logging.critical('cong={}, Pmax={}'.format(lines[0].getprice(times[0],problem),Pmax))
    assert Pline==Pmax and congestion_price == (lmps[1] - lmps[0])
    
@opf.test
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
    Pmin=-100
    generators=[
        make_cheap_gen(bus='A'),
        make_expensive_gen(bus='B')
    ]    
    load=make_load(Pd=225,bus='B')
    lines=[powersystems.Line(Pmin=Pmin, From='B',To='A')]
    problem,times,buses=solve_problem(generators,load,lines=lines)
    Pline = lines[0].P[times[0]]
    lmps=[b.getprice(times[0], problem) for b in buses]
    congestion_price = lines[0].getprice(times[0],problem)
    assert Pline==Pmin and congestion_price == -1*(lmps[1] - lmps[0])


@opf.test
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
    Pmax=50
    Pd=[105,225,302]
    generators=[
        make_cheap_gen(bus='A'),
        make_mid_gen(bus='B'),
        make_expensive_gen(bus='C'),
        ]    
    loads=[
        powersystems.makeLoad(P=Pd[0],bus='A'),
        powersystems.makeLoad(P=Pd[1],bus='B'),
        powersystems.makeLoad(P=Pd[2],bus='C')
        ]
    lines=[
        powersystems.Line(From='A',To='B'),
        powersystems.Line(From='A',To='C', Pmax=Pmax),
        powersystems.Line(From='B',To='C', Pmax=Pmax),
        ]
    times=singletime
    buses=powersystems.make_buses_list(loads,generators)
    problem=solve.create_problem(buses,lines,times)
    problem.solve()
    if problem.solved:
        for g in generators: g.update_vars(times,problem)
    
    num_lmps=len(set(b.getprice(times[0], problem) for b in buses))
    total_load = value(sum(b.Pload(times[0]) for b in buses))
    assert total_load==sum(Pd) and num_lmps>1


if __name__ == "__main__": 
    opf.run()
