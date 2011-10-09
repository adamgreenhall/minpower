'''Test the higher level behavior of the unit commitment'''

from attest import Tests,Assert,assert_hook
import logging,random
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
    lmps = [buses[0].getprice(t,problem) for t in times]
    
    assert lmps==[gen_costs['cheap'],gen_costs['mid'],gen_costs['expensive']]

@uc.test
def rolling():
    '''
    Run a basic unit commitment over 72hrs
    Ensure that the generation meets the load for each time.
    '''
    generators=[powersystems.Generator(costcurvestring='10P+.01P^2')]
    load=make_load(Pdt=[random.randrange(0, 200) for i in range(0,72)])
    problem,times,buses=solve_problem(generators,load)
    load_balanced = all(generators[0].power[t]==buses[0].loads[0].P(t) for t in times)
    assert load_balanced


@uc.test
def load_shedding():
    '''
    Create a single generator with a high limit.
    Create a load that exceeds that limit at t1.
    Ensure that:
    * Pdt1=Pgmax
    * Pshedt1 = Pdt1 - Pmax
    * pricet1 = cost of load shedding
    '''
    Pmax=100
    Pdt1=211
    generators=[make_cheap_gen(Pmax=Pmax)]
    load=make_load(Pdt=[110,Pdt1,110])
    problem,times,buses=solve_problem(generators,load,load_shedding_allowed=True)
    load_t1=buses[0].loads[0].P(times[1])
    load_t1_shed=buses[0].loads[0].shed(times[1])
    price_t1 = buses[0].getprice(times[1],problem)
    assert load_t1==Pmax and load_t1_shed==Pdt1-Pmax and price_t1==config.cost_loadshedding

if __name__ == "__main__": 
    uc.run()
