"""
An optimization command library.
Currently uses pulp but is transitioning to using coopr.
"""

#from config import optimization_package
optimization_package='coopr'

if optimization_package=='pulp':
    import pulp
elif optimization_package=='coopr':
    import coopr.pyomo as pyomo
    try: from coopr.opt.base import solvers as cooprsolver #for coopr version>3.0.4362
    except ImportError:
        #previous versions of coopr
        from coopr.opt.base import solver as cooprsolver
else: raise ImportError('optimization library must be coopr or pulp.')
import logging


if optimization_package=='coopr':
    class Problem(object):
        '''an optimization problem/model based on pyomo'''
        def __init__(self):
            self.model=pyomo.ConcreteModel()
            self.solved=False
        def addObjective(self,expression,sense=pyomo.minimize):
            '''add an objective to the problem'''
            self.model.objective=pyomo.Objective(rule=expression,sense=sense)
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
        def addVar(self,var):
            '''add a single variable to the problem'''
            setattr(self.model, var.name, var)


        def solve(self,solver='cplex'):
            ''' solve the optimization problem.
                valid solvers are {cplex,gurobi,glpk}'''

            logging.info('Solving with {s} ... '.format(s=solver))
            instance=self.model.create()
            opt = cooprsolver.SolverFactory(solver)
            results = opt.solve(instance, suffixes=['.*'])#,keepFiles=True)
            
            if not str(results.solver[0]['Termination condition'])=='optimal':
                msg='problem not solved. Solver terminated with status: "{}"'.format(results.solver[0]['Termination condition'])
                raise OptimizationError(msg)
            else:
                self.solved=True
                logging.info('Problem solved.')
            
            instance.load(results)
        
            def resolvefixvariables(model,instance,solution):
                active_vars= instance.active_components(pyomo.Var)
                for name,var in active_vars.iteritems():
                    if isinstance(var.domain, pyomo.base.IntegerSet): var.fixed=True
                    if isinstance(var.domain, pyomo.base.BooleanSet): var.fixed=True
                instance.preprocess()
                results= opt.solve(instance, suffixes=['.*'])
                instance.load(results)
                return results
                
            results = resolvefixvariables(self.model,instance,results.solution(0))
                    
            self.solution=results.solution(0)

            if solver=='glpk':
                self.objective = self.solution.objective['objective']['Value']
            else: 
                try: self.objective = self.solution.objective['__default_objective__']['Value']
                except AttributeError: 
                    logging.warning('could not get objective value from solver.')
                    self.objective=0
            
            self.constraints = instance.active_components(pyomo.Constraint)
            self.variables = instance.active_components(pyomo.Var)
            
            #print self.constraints['powerBalance_i0t01'][None].dual
            #print self.dual('powerBalance_i0t01')
            #raise NotImplementedError
            
            return 
        def dual(self,constraintname,index=None):
            return self.constraints[constraintname][index].dual

        def __getattr__(self,name):
            try: return getattr(self.model,name)
            except AttributeError:
                msg='the model has no variable/constraint/attribute named "{n}"'.format(n=name)
                raise AttributeError(msg)

    def value(var,problem=None):
        '''value of an optimization variable'''
        #var=result.solution.variable[name]
        if problem is None: return var
        
        varname=var.name
        try: return problem.variables[varname].value
        except KeyError:
            print 'variables are {}'.format([v for v in problem.variable])
            raise
        except AttributeError:
            if type(varname)==pyomo.base.expr._SumExpression: print 'sum expression'
            #print dir(var)
            #var.display()
            #print var.as_numeric()
            print varname
            print problem.variables
            #print problem.variable[varname]
            #print problem.Variable[varname].value
            raise
    def dual(constraint):
        '''dual value of an optimization constraint'''
        try: return constraint.dual
        except AttributeError: return 0
        #return solution.Constraint[constraint.name]['Dual']

    def sumVars(variables): return sum(variables)
    def newProblem(): return Problem()
    def newVar(name='',kind='Continuous',low=-1000000,high=1000000):
        '''create an optimization variable'''
        
        kindmap = dict(Continuous=pyomo.Reals, Binary=pyomo.Boolean)
        return pyomo.Var(name=name,bounds=(low,high),domain=kindmap[kind])
    def solve(problem,solver='cplex'): return problem.solve(solver)

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
        try:
            if   solver.lower()=='cplex':  out=problem.solve(pulp.CPLEX_CMD(msg=0)),
            elif solver.lower()=='glpk':   out=problem.solve(pulp.GLPK_CMD(msg=0)),
            elif solver.lower()=='gurobi': out=problem.solve(pulp.GUROBI(msg=0))
            elif solver.lower()=='coin':   out=problem.solve(pulp.COINMP_DLL(msg=0))
            else:
                msg='Couldnt find the solver "{}"'.format(solver)
                raise OptimizationError(msg)
        except pulp.solvers.PulpSolverError:
            problem.status=0
            out=None

        if problem.status:
            logging.info('{stat} in {time:0.4f} sec'.format(
                stat=problem.statusText(),
                time=problem.solutionTime))
        #else: logging.warning(problem.statusText())

        return out
    def value(variable):
        '''value of an optimization variable'''
        try: return pulp.value(variable)
        except AttributeError: return variable
    def dual(constraint,default=None):
        '''dual value of an optimization constraint'''
        try: return constraint.pi
        except AttributeError:
            logging.warning('Duals information not supported by GLPK.')
            return default

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
