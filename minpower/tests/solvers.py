'''Test the all of the solver links'''

from minpower import optimization

def testall(stop_on_error=False):
    prob=optimization.newProblem()
    x= prob.newVar('x',low=0,high=3)
    y= prob.newVar('y',low=0,high=1)
    prob.addObjective(y-4*x)
    prob.addConstraints(dict(theconstr=(x+y<=2)))

    for solver in ['glpk','cplex','gurobi']:
        try: 
            optimization.solve(prob,solver)
            print solver,'solved problem, status: ', 
            print prob.statusText()
        except:
            print solver,' failed'
            if stop_on_error: raise

if __name__ == "__main__": testall()
