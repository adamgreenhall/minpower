'''Test the constraint behavior of an OPF'''

from attest import Tests,Assert,assert_hook
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.optimization import value

from test_utils import solve_problem,make_loads_times,make_cheap_gen,make_mid_gen,make_expensive_gen,singletime

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
    lines=[powersystems.Line(Pmax=Pmax, From='A',To='B')]
    power_system,times=solve_problem(generators,lines=lines,get_duals=True,**make_loads_times(Pd=225,bus='B'))
    Pline = lines[0].power(times[0])
    lmps=[b.price(times[0]) for b in power_system.buses]
    congestion_price = lines[0].price(times[0])
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
    lines=[powersystems.Line(Pmin=Pmin, From='B',To='A')]
    power_system,times=solve_problem(generators,lines=lines,get_duals=True,**make_loads_times(Pd=225,bus='B'))
    Pline = lines[0].power(times[0])
    lmps=[b.price(times[0]) for b in power_system.buses]
    congestion_price = lines[0].price(times[0])
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
    power_system,times=solve_problem(generators,times=singletime,loads=loads,lines=lines,get_duals=True)
    num_lmps=len(set(b.price(times[0]) for b in power_system.buses))
    total_load = value(sum(b.Pload(times[0]) for b in power_system.buses))
    assert total_load==sum(Pd) and num_lmps>1


if __name__ == "__main__": 
    opf.run()
