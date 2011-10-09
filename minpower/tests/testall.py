from attest import Tests
all_tests=Tests([
    'solvers.solvers',
    'generators.generation',
    'unit_commitment.uc',
    'opf.opf',
    'bidding.bidding'
    ])

if __name__ == "__main__": all_tests.run()
