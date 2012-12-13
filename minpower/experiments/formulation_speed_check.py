from minpower import solve,config
import sys

def test(resultsfile='out.txt',logfile='out.log'):
    sys.stdout = open(resultsfile, 'w+')
    solve.solve_problem(
        datadir='/home/adam/ercot-data/ercot-2010-test-system/',
        shell=True,
        problemfile=False,
        visualization=False,
        csv=False,
        solver='cplex',
        num_breakpoints=10,
        hours_commitment=24,
        hours_commitment_overlap=12,
        get_duals=False,
        logging_file=logfile,
        solution_file=False
        )

if __name__ == "__main__": 
    config.updown_formulation=sys.argv[1]
    filename=config.updown_formulation.replace(' ','-')
    test(resultsfile=filename+'.txt',logfile=filename+'.log')