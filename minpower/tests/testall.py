"""
Run all of the unit tests, currently: 
bidding, generation, opf, solvers, unit commitment
 
This module uses the Attest package testing framework.
"""

from attest import Tests

if __name__ == "__main__": 
    all_tests=Tests([
    'solvers.solvers',
    'generators.generation',
    'unit_commitment.uc',
    'opf.opf',
    'bidding.bidding'
    ])
    all_tests.run()
