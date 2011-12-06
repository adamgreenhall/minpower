"""
Run all of the unit tests in  
    :mod:`tests.solvers`,
    :mod:`tests.generators`,
    :mod:`tests.unit_commitment`,
    :mod:`tests.opf`, and
    :mod:`tests.bidding`
    
Most unit tests are designed to ensure that a single constraint is working.  
This module uses the Attest package testing framework.
"""

from attest import Tests
import logging
logging.basicConfig( level=logging.CRITICAL, format='%(levelname)s: %(message)s')
if __name__ == "__main__": 
    all_tests=Tests([
    'solvers.solvers',
    'generators.generation',
    'unit_commitment.uc',
    'opf.opf',
    'bidding.bidding'
    ])
    all_tests.run()
