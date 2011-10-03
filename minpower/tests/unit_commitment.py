'''Test the constraint behavior of the generators'''

from attest import Tests,Assert
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')

from minpower import optimization,powersystems,schedule,solve,config
from minpower.powersystems import Generator
from minpower.optimization import value

uc = Tests()

@uc.test
def prices():
    '''
    Run a basic unit commitment. 
    Ensure that the correct LMPs are returned for all times.
    '''
    
    
    
    
if __name__ == "__main__": 
    uc.run()