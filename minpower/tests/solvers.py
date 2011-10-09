'''Test the all of the solver links'''

from attest import Tests,assert_hook
from minpower import optimization, config
solvers = Tests()

def simple_problem():
    prob=optimization.newProblem()
    x= optimization.newVar('x',low=0,high=3)
    y= optimization.newVar('y',low=0,high=1)
    prob.addVariables([x,y])
    prob.addObjective(y-4*x)
    prob.addConstraints(dict(theconstr=(x+y<=2)))    
    return prob 

def test_one_solver(solver_name):
    prob=simple_problem()
    optimization.solve(prob,solver=solver_name)
    return prob.status

@solvers.test
def cplex():
    '''Test each available solver on a simple problem'''
    if 'cplex' in config.available_solvers:
        assert test_one_solver('cplex')

@solvers.test
def glpk():
    '''Test the glpk solver on a simple problem'''
    if 'glpk' in config.available_solvers:
        assert test_one_solver('glpk')

@solvers.test
def gurobi():
    '''Test the gurobi solver on a simple problem'''
    if 'gurobi' in config.available_solvers:
        assert test_one_solver('gurobi')
        
if __name__ == "__main__": solvers.run()
