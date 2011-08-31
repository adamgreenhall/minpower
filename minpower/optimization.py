"""
An optimization command library.
Currently uses pulp but is transitioning to using coopr.
"""

from config import optimization_package

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
import config

if optimization_package=='coopr':
    class Problem(object):
        '''an optimization problem/model based on pyomo'''
        def __init__(self):
            self.model=pyomo.ConcreteModel()
            self.solved=False
        def addObjective(self,expression,sense=pyomo.minimize):
            '''add an objective to the problem'''
            self.model.objective=pyomo.Objective(rule=expression,sense=sense)
        def addVar(self,var):
            '''add a single variable to the problem'''
            try: setattr(self.model, var.name, var)
            except AttributeError: pass #just a number, don't add to vars
        def addConstraints(self,constraintsD):
            '''add a dictionary of constraints (keyed by name) to the problem'''
            try:
                for name,expression in constraintsD.iteritems(): self.addConstraint(name,expression)
            except AttributeError:
                if constraintsD is None: pass
                else: raise AttributeError('addConstraints takes a dictionary of constraints argument')
        def addConstraint(self,name,expression):
            '''add a single constraint to the problem'''
            setattr(self.model, name, pyomo.Constraint(name=name,rule=expression))
        def dual(self,constraintname,index=None):
            '''dual value of an optimization constraint'''
            return self.constraints[constraintname][index].dual


        def solve(self,solver=config.optimization_solver):
            ''' solve the optimization problem.
                valid solvers are {cplex,gurobi,glpk}'''

            logging.info('Solving with {s} ... '.format(s=solver))
            instance=self.model.create()
            opt = cooprsolver.SolverFactory(solver)
            results = opt.solve(instance, suffixes=['.*'])#,keepFiles=True)

            self.statusText = str(results.solver[0]['Termination condition'])
            if not self.statusText =='optimal':
                logging.warning('problem not solved. Solver terminated with status: "{}"'.format(self.statusText))
                self.status=False
            else:
                self.status=True
                logging.info('Problem solved.')

            #need to fix this up for coopr
            self.solutionTime = 0

            instance.load(results)


            def resolvefixvariables(model,instance):
                active_vars= instance.active_components(pyomo.Var)
                for name,var in active_vars.iteritems():
                    if isinstance(var.domain, pyomo.base.IntegerSet): var.fixed=True
                    if isinstance(var.domain, pyomo.base.BooleanSet): var.fixed=True
                instance.preprocess()
                try: results= opt.solve(instance, suffixes=['.*'])
                except RuntimeError:
                    print 'coopr raised an error in solving. re-trying, with debugging.'
                    results= opt.solve(instance, suffixes=['.*'],keepFiles=True)    
                instance.load(results)
                return results

            results = resolvefixvariables(self.model,instance)

            solution=results.solution(0)

            if solver=='glpk':
                self.objective = solution.objective['objective']['Value']
            else: 
                try: self.objective = solution.objective['__default_objective__']['Value']
                except AttributeError: 
                    logging.error('could not get objective value from solver.')
                    self.objective=0

            self.constraints = instance.active_components(pyomo.Constraint)
            self.variables =  instance.active_components(pyomo.Var)

            return 

        def __getattr__(self,name):
            try: return getattr(self.model,name)
            except AttributeError:
                msg='the model has no variable/constraint/attribute named "{n}"'.format(n=name)
                raise AttributeError(msg)

    def value(variable,problem=None):
        '''value of an optimization variable'''
        if problem is None: return variable #just a number

        try: varname=variable.name
        except AttributeError: return variable #just a number

        return problem.variables[varname].value

    def sumVars(variables): return sum(variables)
    def newProblem(): return Problem()
    def newVar(name='',kind='Continuous',low=-1000000,high=1000000):
        '''create an optimization variable'''

        kindmap = dict(Continuous=pyomo.Reals, Binary=pyomo.Boolean, Boolean=pyomo.Boolean)
        return pyomo.Var(name=name,bounds=(low,high),domain=kindmap[kind])
    def solve(problem,solver=config.optimization_solver): return problem.solve(solver)


elif optimization_package=='pulp':
    class Problem(pulp.LpProblem):
        '''an optimization problem'''

        def addObjective(self,expression,name='objective'):
            '''add an objective to the problem'''
            self+=expression,name
        def addVar(self,var):
            #no need to add variables to the model for puLP
            pass
        def addConstraints(self, constraintsD):
            '''add a dictionary of constraints (keyed by name) to the problem'''
            try:
                for name,expression in constraintsD.iteritems(): self.addConstraint(expression,name)
            except AttributeError:
                if constraintsD is None: pass
                else: raise AttributeError('addConstraints takes a dictionary of constraints argument')
            
        def dual(self,constraintname,default=0):
            '''dual value of an optimization constraint'''
            constraint=self.constraints[constraintname]
            try: return constraint.pi
            except AttributeError:
                logging.debug('Duals information not supported by GLPK.')
                return default

        def write(self,filename):
            '''write the problem to a human-readable file'''
            self.writeLP(filename)
        def save(self,filename='problem.dat'):
            from yaml import dump
            with open(filename, 'w+') as file: dump(self, file)


    def value(variable,problem=None):
        '''value of an optimization variable'''
        try: return pulp.value(variable)
        except AttributeError: return variable

    def sumVars(variables):
        '''sums a list of optimization variables'''
        return pulp.lpSum(variables)
    def newProblem(name='problem',kind=pulp.LpMinimize):
        '''create a new problem'''
        return Problem(name=name,sense=kind)
    def newVar(name='',kind='Continuous',low=-1000000,high=1000000):
        '''create an optimization variable'''
        #note that if binary variable, pulp will reset the bounds to (0,1)
        #note that if using glpk, bounds of -inf and inf produces error
        return pulp.LpVariable(name=name,cat=kind,lowBound=low,upBound=high)

    def solve(problem,solver=config.optimization_solver):
        '''solve the optimization problem'''
        logging.info('Solving with {s} ... '.format(s=solver))
        solvermap = dict(
            glpk=pulp.GLPK_CMD,
            cplex=pulp.CPLEX_CMD,
            gurobi=pulp.GUROBI,
            coin=pulp.pulp.COINMP_DLL,
            )

        try: out=problem.solve(solvermap[solver.lower()](msg=0))
        except pulp.solvers.PulpSolverError:
            problem.status=0
            out=None

        problem.statusText=pulp.LpStatus[problem.status]
        if problem.status:
            logging.info('{stat} in {time:0.4f} sec'.format(
                stat=problem.statusText,
                time=problem.solutionTime))
        #else: logging.warning(problem.statusText())

        return out

class OptimizationError(Exception):
    def __init__(self, ivalue):
        if ivalue: self.value=ivalue
        else: self.value="Optimization Error: there was a problem"
        Exception.__init__( self, self.value)

    def __str__(self): return self.value
