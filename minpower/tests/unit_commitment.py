'''Test the higher level behavior of the unit commitment'''

from attest import Tests,Assert
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.optimization import value

from test_utils import *

uc = Tests()

@uc.test
def prices():
    '''
    Run a basic unit commitment. 
    Ensure that the correct LMPs are returned for all times.
    '''
    generators=[
        make_cheap_gen(Pmax=100),
        make_mid_gen(Pmax=20),
        make_expensive_gen()
    ]
    load=make_load(Pdt=[80,110,130])
    problem,times,buses=solve_problem(generators,load)
    lmps = Assert([buses[0].getprice(t,problem) for t in times])
    
    assert lmps==[gen_costs['cheap'],gen_costs['mid'],gen_costs['expensive']]
    
if __name__ == "__main__": 
    uc.run()
