'''Test the higher level behavior of the unit commitment'''

from attest import Tests,Assert,assert_hook
import logging,random
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.optimization import value

from test_utils import solve_problem,make_loads_times,make_cheap_gen,make_mid_gen,make_expensive_gen,gen_costs

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
    power_system,times=solve_problem(generators,get_duals=True,**make_loads_times(Pdt=[80,110,130]))
    lmps = [power_system.buses[0].price(t) for t in times]
    
    assert lmps==[gen_costs['cheap'],gen_costs['mid'],gen_costs['expensive']]

@uc.test
def rolling():
    '''
    Run a basic unit commitment over 72hrs
    Ensure that the generation meets the load for each time.
    '''
    generators=[powersystems.Generator(costcurvestring='10P+.01P^2')]
    Pdt=[random.randrange(0, 200) for i in range(0,72)]
    power_system,times=solve_problem(generators,**make_loads_times(Pdt=Pdt))
    load=power_system.loads()[0]
    load_balanced = all(generators[0].power(t)==load.power(t) for t in times)
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
    Pdt=[110,Pdt1,110]
    power_system,times=solve_problem(generators,get_duals=True,load_shedding_allowed=True,**make_loads_times(Pdt=Pdt))
    load=power_system.loads()[0]
    load_t1=load.power(times[1],evaluate=True)
    load_t1_shed=load.shed(times[1],evaluate=True)
    price_t1 = power_system.buses[0].price(times[1])
    assert load_t1==Pmax 
    assert load_t1_shed==Pdt1-Pmax
    assert price_t1==config.cost_load_shedding

if __name__ == "__main__": 
    uc.run()
