"""
An optimization command library. 
Currently uses pulp but is transitioning to using coopr.
"""

from config import optimization_package

if optimization_package=='pulp':
    import pulp
elif optimization_package=='coopr':
    import coopr.pyomo as pyomo
    from coopr.opt.base import solver as cooprsolver
else: raise ImportError('optimization library must be coopr or pulp.')
import logging



if optimization_package=='coopr':
    class Problem(object):
        '''an optimization problem/model based on pyomo'''
        def __init__(self):
            self.model=pyomo.AbstractModel()
        
        def addObjective(self,expression,kind=pyomo.minimize):
            '''add an objective to the problem'''
            self.model.objective=pyomo.Objective(rule=expression,sense=kind)
        def addConstraints(self,constraintsD):
            '''add a dictionary of constraints (keyed by name) to the problem'''
            try: 
                for name,val in constraintsD.iteritems(): self.addConstraint(name,val)
            except AttributeError: 
                if constraintsD is None: pass
                else: raise AttributeError('addConstraints takes a dictionary of constraints argument')        
        def addConstraint(self,name,expression):
            '''add a single constraint to the problem'''
            setattr(self.model, name, pyomo.Constraint(name=name,rule=expression))
        def addVar(self,name,kind='Reals',low=-float('inf'),high=float('inf')):
            '''add a single variable to the problem'''
            #TODO: what kinds are acceptable (how to get Binary)
            setattr(self.model, name, pyomo.Var(name=name,bounds=(low,high) ))#,domain=kind))

        def solve(self,solver='cplex'):
            ''' solve the optimization problem. 
                valid solvers are {cplex,gurobi,glpk}'''
            
            logging.info('Solving with {s} ... '.format(s=solver))
            instance=self.model.create()
            opt = cooprsolver.SolverFactory(solver)
            results = opt.solve(instance, suffixes=['.*'])
            instance.update_results(results)
            self.results=results
            return results
        def __getattr__(self,name):
            try: return getattr(self.model,name)
            except AttributeError:
                raise AttributeError('the model has no variable/constraint/... named "{n}"'.format(n=name))
            
    def value(name,result):
        '''value of an optimization variable'''
        var=result.solution.variable[name]
        return var.Value
    def dual(name, result):
        '''dual value of an optimization constraint'''
        cons=result.solution.constraint[name]
        try: return cons.dual
        except AttributeError: return None #not active constraint

    def sumVars(variables): return sum(variables)
    def newProblem(*args,**kwargs): return Problem_coopr()
    def solve(problem,solver,verbose): return problem.solve(solver,verbose)

elif optimization_package=='pulp':
    class Problem(pulp.LpProblem):
        '''an optimization problem'''
        
        def addObjective(self,expression,name='objective'):
            '''add an objective to the problem'''
            self+=expression,name
        def newVar(self,*args,**kwargs):
            #low=-float('inf'),high=float('inf')):
            '''create an optimization variable'''
            return newVar(*args,**kwargs)
        def addConstraints(self, constraintsD):
            '''add a dictionary of constraints (keyed by name) to the problem'''
            try: 
                for name,val in constraintsD.iteritems(): self=addConstraint(self,val,name)
            except AttributeError: 
                if constraintsD is None: pass
                else: raise AttributeError('addConstraints takes a dictionary of constraints argument')
        
        def write(self,filename):
            '''write the problem to a human-readable file'''
            self.writeLP(filename)
        def statusText(self): 
            '''solution status of the problem'''
            return pulp.LpStatus[self.status]
        def save(self,filename='problem.dat'):
            from yaml import dump
            with open(filename, 'w+') as file: dump(self, file)
        

    def solve(problem,solver='cplex'):
        '''solve the optimization problem'''
        logging.info('Solving with {s} ... '.format(s=solver))
        
        if   solver.lower()=='cplex':  out=problem.solve(pulp.CPLEX_CMD(msg=0)),
        elif solver.lower()=='glpk':   out=problem.solve(pulp.GLPK(msg=0)),
        elif solver.lower()=='gurobi': out=problem.solve(pulp.GUROBI(msg=0))
        
        if problem.status: 
            logging.info('{stat} in {time:0.4f} sec'.format(
                stat=problem.statusText(),
                time=problem.solutionTime)) 
        else: logging.warning(problem.statusText())
        return out
    def value(variable):
        '''value of an optimization variable'''
        try: return pulp.value(variable)
        except AttributeError: return variable
    def dual(constraint):    
        '''dual value of an optimization constraint'''
        try: return constraint.pi
        except AttributeError:
            logging.warning('Duals information not supported by GLPK.')
            return None

    def sumVars(variables): 
        '''sums a list of optimization variables'''
        return pulp.lpSum(variables)
    def newProblem(name='problem',kind=pulp.LpMinimize):
        '''create a new problem'''
        return Problem(name=name,sense=kind)
    def addConstraint(problem,expression,name=''):
        '''add a single constraint to the problem'''
        problem+=expression,name
        return problem
    def newVar(name='',kind='Continuous',low=-1000000,high=1000000):
        '''create an optimization variable'''
        #note that if binary variable, pulp will reset the bounds to (0,1)
        #note that if using glpk, bounds of -inf and inf produces error
        return pulp.LpVariable(name=name,cat=kind,lowBound=low,upBound=high)

class OptimizationError(Exception):
    def __init__(self, ivalue):
        if ivalue: self.value=ivalue
        else: self.value="Optimization Error: there was a problem"
        Exception.__init__( self, self.value)

    def __str__(self): return self.value
