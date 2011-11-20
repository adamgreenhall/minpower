"""
An optimization command library.
Currently uses pulp but is transitioning to using coopr.
"""

import coopr.pyomo as pyomo
#from pyutilib.misc import Options as cooprOptions
#import coopr.pyomo.scripting.util as cooprUtil
from coopr.opt.base import solvers as cooprsolver

variable_kinds = dict(Continuous=pyomo.Reals, Binary=pyomo.Boolean, Boolean=pyomo.Boolean)

import logging,time
import config
from commonscripts import update_attributes,show_clock

<<<<<<< HEAD
if optimization_package=='coopr':
    class Problem(object):
        '''an optimization problem/model based on pyomo'''
        def __init__(self):
<<<<<<< HEAD
            self.model=pyomo.ConcreteModel()
            self.solved=False
<<<<<<< HEAD
        def addObjective(self,expression,sense=pyomo.minimize):
<<<<<<< HEAD
=======
            self.model=pyomo.AbstractModel()

        def addObjective(self,expression,kind=pyomo.minimize):
>>>>>>> tiny stuff
            '''add an objective to the problem'''
            self.model.objective=pyomo.Objective(rule=expression,sense=sense)
=======
            '''add an objective to the problem'''            
            self.model.objective=pyomo.Objective(name='objective',rule=expression,sense=sense)
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> added objective name
=======
        def addVariables(self,vars): [self.addVar(v) for v in vars]
>>>>>>> needed to make opt.solve arguments keyword in order for them to get passed correctly
=======
        def addVariables(self,variables): [self.addVar(v) for v in variables]
>>>>>>> cleanup
        def addVar(self,var):
=======
        def add_objective(self,expression,sense=pyomo.minimize):
            '''add an objective to the problem'''            
            self.model.objective=pyomo.Objective(name='objective',rule=expression,sense=sense)
#        def addVariables(self,variables): [self.add_variable(v) for v in variables]
        def add_variable(self,variable):
>>>>>>> first working pass through solver (results still needs major rework
            '''add a single variable to the problem'''
            try: self._add_component(variable.name,variable) #setattr(self.model, var.name, var)
            except AttributeError: pass #just a number, don't add to vars
        def add_constraint(self,constraint):
            '''add a single constraint to the problem'''
            self._add_component(constraint.name,constraint)
            #setattr(self.model, constraint.name, constraint)

#        def addConstraints(self,constraintsD):
#            '''add a dictionary of constraints (keyed by name) to the problem'''
#            try:
#                for name,expression in constraintsD.iteritems(): self.add_constraint(name,expression)
#            except AttributeError:
#                if constraintsD is None: pass
#                else: raise AttributeError('addConstraints takes a dictionary of constraints argument')
        def dual(self,constraintname,index=None):
            '''dual value of an optimization constraint'''
            return self.constraints[constraintname][index].dual


        def solve(self,solver=config.optimization_solver,problem_filename=False):
            ''' solve the optimization problem.
                valid solvers are {cplex,gurobi,glpk}'''

            
            current_log_level = logging.getLogger().getEffectiveLevel()      
                        
            def cooprsolve(instance,opt=None,suffixes=['dual'],keepFiles=False):
                if not keepFiles: logging.getLogger().setLevel(logging.WARNING)
=======
class Problem(object):
    '''an optimization problem/model based on pyomo'''
    def __init__(self):
        self.model=pyomo.ConcreteModel()
        self.solved=False
    def add_objective(self,expression,sense=pyomo.minimize):
        '''add an objective to the problem'''            
        self.model.objective=pyomo.Objective(name='objective',rule=expression,sense=sense)
    def add_variable(self,variable):
        '''add a single variable to the problem'''
        try: self._add_component(variable.name,variable)
        except AttributeError: pass #just a number, don't add to vars
    def add_constraint(self,constraint):
        '''add a single constraint to the problem'''
        self._add_component(constraint.name,constraint)
    def solve(self,solver=config.optimization_solver,problem_filename=False,get_duals=True):
        '''
        Solve the optimization problem.
        
        :param solver: name of solver (lowercase string).
        :param problem_filename: write MIP problem formulation to a file, if a file name is specified
        :param get_duals: get the duals, or prices, of the optimization problem
        '''
        
        current_log_level = logging.getLogger().getEffectiveLevel()      
                    
        def cooprsolve(instance,opt=None,suffixes=['dual'],keepFiles=False):
            if not keepFiles: logging.getLogger().setLevel(logging.WARNING)
            if opt is None: 
                opt = cooprsolver.SolverFactory(solver)
>>>>>>> dropped pulp from optimization module. clean up docstrings.
                if opt is None: 
                    msg='solver "{}" not found'.format(solver)
                    raise OptimizationError(msg)
            
            start = time.time()
            results= opt.solve(instance,suffixes=suffixes,keepFiles=keepFiles)
            #results,opt=cooprUtil.apply_optimizer(options,instance)
            elapsed = (time.time() - start)
            logging.getLogger().setLevel(current_log_level)
            return results,elapsed
        
        
        logging.info('Solving with {s} ... {t}'.format(s=solver,t=show_clock()))
        instance=self.model.create()
        logging.debug('... model created ... {t}'.format(t=show_clock()))     
        results,elapsed=cooprsolve(instance)
        
        self.statusText = str(results.solver[0]['Termination condition'])
        if not self.statusText =='optimal':
            logging.critical('problem not solved. Solver terminated with status: "{}"'.format(self.statusText))
            self.status=self.solved=False
        else:
            self.status=self.solved=True
            self.solutionTime =elapsed #results.Solver[0]['Wallclock time']
            logging.info('Problem solved in {}s.'.format(self.solutionTime))
            logging.debug('... {t}'.format(t=show_clock()))
        
        if problem_filename:
            logging.disable(logging.CRITICAL) #disable coopr's funny loggings when writing lp files.  
            self.write(problem_filename)
            logging.disable(current_log_level)
                
        if not self.status: return
        
        #instance.load(results)
        instance._load_solution(results.solution(0), ignore_invalid_labels=True )
        logging.debug('... solution loaded ... {t}'.format(t=show_clock()))

        
        def resolvefixvariables(instance,results):
            active_vars= instance.active_components(pyomo.Var)
            need_to_resolve=False
            for _,var in active_vars.items():
                if isinstance(var.domain, pyomo.base.IntegerSet) or isinstance(var.domain, pyomo.base.BooleanSet):
                    var.fixed=True
                    need_to_resolve=True
            
            if not need_to_resolve: return instance,results
            logging.info('resolving fixed-integer LP for duals')
            instance.preprocess()
            try:
                results,elapsed=cooprsolve(instance)
                self.solutionTime+=elapsed
            except RuntimeError:
                logging.error('coopr raised an error in solving. keep the files for debugging.')
                results= cooprsolve(instance, keepFiles=True)    
            
<<<<<<< HEAD
            instance.load(results)
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
        
<<<<<<< HEAD
            def resolvefixvariables(instance,solution):
                for varname in solution.Variable: getattr(instance,varname).fixed=True
=======
            def resolvefixvariables(model,instance,solution):
=======


            def resolvefixvariables(model,instance):
>>>>>>> working coopr and pulp mix
=======
            

            
            def resolvefixvariables(instance,results):
>>>>>>> clean up coopr solve()
                active_vars= instance.active_components(pyomo.Var)
                need_to_resolve=False
                for name,var in active_vars.iteritems():
                    if isinstance(var.domain, pyomo.base.IntegerSet) or isinstance(var.domain, pyomo.base.BooleanSet):
                        var.fixed=True
                        need_to_resolve=True
                
                if not need_to_resolve: return instance,results
                logging.info('resolving fixed-integer LP for duals')
                instance.preprocess()
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> working dual resolve. with glpk! need to formulate into the methods.
                results= opt.solve(instance, suffixes=['.*'])
=======
                try: results= opt.solve(instance, suffixes=['.*'])
=======
                try: results= opt.solve(instance, suffixes=['dual'])
>>>>>>> just return duals on resolve (no slack info)
=======
                try:
                    results,elapsed=cooprsolve(instance)
                    self.solutionTime+=elapsed
>>>>>>> better logging w. coopr, solve time, solver calls. changed line dual to be its flow constraint. better logging level for testall.
                except RuntimeError:
                    logging.error('coopr raised an error in solving. keep the files for debugging.')
<<<<<<< HEAD
                    results= opt.solve(instance, suffixes=['.*'],keepFiles=True)    
>>>>>>> working coopr and pulp mix
=======
                    results= cooprsolve(instance, keepFiles=True)    
>>>>>>> changed fix_timevars to fix_vars in Generator(). fixed reporting on load shedding.
                instance.load(results)
                return instance,results

<<<<<<< HEAD
<<<<<<< HEAD
            results = resolvefixvariables(self.model,instance)

            solution=results.solution(0)
            
            #need to fix this to depend on result, not solution object
            if solver=='glpk':
                self.objective = solution.objective['objective']['Value']
            else: 
                try: self.objective = solution.objective['__default_objective__']['Value']
                except AttributeError: 
                    logging.error('could not get objective value from solver.')
                    self.objective=0
<<<<<<< HEAD
            

            self.constraints = instance.active_components(pyomo.Constraint)
<<<<<<< HEAD
            #print 'there are {} constraints in the solution'.format(len(self.solution.constraint))
            #self.constraintnames = [c[4:len(c)-1] for c in self.constraints]
            #self.constraintnames_full = [c for c in self.constraints]
        
            print 'objective=',self.objective
<<<<<<< HEAD
            print self.dual('powerBalance_i0t01')
=======
            for nm,const in self.constraints.iteritems():
                print nm
                print type(const)
                for c in const: print const[c].dual

            #print self.constraints['powerBalance_i0t01']['Dual']
            #print self.dual('powerBalance_i0t01')
>>>>>>> working dual resolve. with glpk! need to formulate into the methods.
            raise NotImplementedError
            
            return 
        def dual(self,constraintname):
            if constraintname not in self.constraintnames: 
                msg='constraint name not found in problem constraints.'
                raise AttributeError(msg)
            idx=self.constraintnames.index(constraintname)
            fullname=self.constraintnames_full[idx]
            try: return self.constraints[fullname]['Dual']
            except AttributeError:
                print 'getting dual for "{}"'.format(fullname)
                print self.constraints
                print self.constraints[fullname]
                raise

=======
            self.variables = instance.active_components(pyomo.Var)
            
            #print self.constraints['powerBalance_i0t01'][None].dual
            #print self.dual('powerBalance_i0t01')
            #raise NotImplementedError
            
            return 
        def dual(self,constraintname,index=None):
            return self.constraints[constraintname][index].dual
>>>>>>> duals now working. variable value structure changed for coopr.
=======
=======
            instance,results = resolvefixvariables(instance,results)
<<<<<<< HEAD
>>>>>>> clean up coopr solve()

=======
>>>>>>> dont try to do fixed resolve for infeasible solution
=======
            try: instance,results = resolvefixvariables(instance,results)
            except RuntimeError:
                logging.error('in re-solving for the duals. the duals will be set to default value.')
                
>>>>>>> if glpk re-solve breaks, just finish without the duals
                    
=======
            instance,results = resolvefixvariables(instance,results)
            
            #get solution information                     
>>>>>>> debug polynomial models
=======
=======
            #instance.load(results)
            instance._load_solution(results.solution(0), ignore_invalid_labels=True )
<<<<<<< HEAD
>>>>>>> rough optimization object model for generator. unit and integration tested.
            
=======
            return instance,results
>>>>>>> dropped pulp from optimization module. clean up docstrings.

        if get_duals: 
            try: instance,results = resolvefixvariables(instance,results)
            except RuntimeError:
                logging.error('in re-solving for the duals. the duals will be set to default value.')
            logging.debug('... LP problem solved ... {t}'.format(t=show_clock()))    
                
<<<<<<< HEAD
                #instance.load(results)
                instance._load_solution(results.solution(0), ignore_invalid_labels=True )
                return instance,results

            try: instance,results = resolvefixvariables(instance,results)
            except RuntimeError:
                logging.error('in re-solving for the duals. the duals will be set to default value.')
                
                    
>>>>>>> fix for gen limits conflict. improved some test cases. enabled problem writing (still just LP not MIP).
            try: self.objective = results.Solution.objective['objective'].value #instance.active_components(pyomo.Objective)['objective']
            except AttributeError:
                self.objective = results.Solution.objective['__default_objective__'].value
                
            self.constraints = instance.active_components(pyomo.Constraint)
            self.variables =   instance.active_components(pyomo.Var)

            return 
<<<<<<< HEAD

>>>>>>> working coopr and pulp mix
=======
        def value(self,name):
            try: 
                return getattr(self.model,name).value
            except TypeError: #name is not a string
                return name.value
<<<<<<< HEAD
        
>>>>>>> testing of ramp rates. added conditional initial ramp rates.
=======
>>>>>>> cleared up dual problem (old coopr solution index=None)
        def __getattr__(self,name):
            try: return getattr(self.model,name)
            except AttributeError:
<<<<<<< HEAD
                msg='the model has no variable/constraint/attribute named "{n}"'.format(n=name)
                raise AttributeError(msg)

<<<<<<< HEAD
<<<<<<< HEAD
    def value(var,solution=None):
=======
                raise AttributeError('the model has no variable/constraint/... named "{n}"'.format(n=name))

    def value(name,result):
>>>>>>> tiny stuff
=======
    def value(var,problem=None):
>>>>>>> duals now working. variable value structure changed for coopr.
=======
    def value(variable,problem=None):
>>>>>>> working coopr and pulp mix
        '''value of an optimization variable'''
        if problem is None: 
            try: 
                return variable.value
            except AttributeError:
                return variable #just a number
        else:
            try: varname=variable.name
            except AttributeError: return variable #just a number
            return problem.variables[varname].value
    def dual(constraint,index=None):
        return constraint[index].dual
    def sum_vars(variables): return sum(variables)
    def newProblem(): return Problem()
    def new_variable(name='',kind='Continuous',low=-1000000,high=1000000):
        '''create an optimization variable'''
        kindmap = dict(Continuous=pyomo.Reals, Binary=pyomo.Boolean, Boolean=pyomo.Boolean)
        return pyomo.Var(name=name,bounds=(low,high),domain=kindmap[kind])
<<<<<<< HEAD
    def new_constraint(name,expression): return pyomo.Constraint(name=name,rule=expression)
    def solve(problem,solver=config.optimization_solver): return problem.solve(solver)
=======
>>>>>>> rewrote Problem.sovle for pulp


elif optimization_package=='pulp':
    class Problem(pulp.LpProblem):
        '''an optimization problem'''

        def add_objective(self,expression,name='objective'):
            '''add an objective to the problem'''
            self+=expression,name
        def add_variable(self,var):
            #no need to add variables to the model for puLP
            pass
        def addConstraints(self, constraintsD):
            '''add a dictionary of constraints (keyed by name) to the problem'''
            try:
                for name,expression in constraintsD.iteritems(): self.add_constraint(expression,name)
            except AttributeError:
                if constraintsD is None: pass
                else: raise AttributeError('addConstraints takes a dictionary of constraints argument')
=======
        try: self.objective = results.Solution.objective['objective'].value #instance.active_components(pyomo.Objective)['objective']
        except AttributeError:
            self.objective = results.Solution.objective['__default_objective__'].value
>>>>>>> dropped pulp from optimization module. clean up docstrings.
            
        self.constraints = instance.active_components(pyomo.Constraint)
        self.variables =   instance.active_components(pyomo.Var)

        return 
    def __getattr__(self,name):
        try: return getattr(self.model,name)
        except AttributeError:
            msg='the model has no variable/constraint/attribute named "{n}"'.format(n=name)
            raise AttributeError(msg)

def value(variable):
    '''
    Value of an optimization variable after the problem is solved.
    If passed a numeric value, will return the number.
    '''
    try: return variable.value
    except AttributeError: return variable #just a number

def dual(constraint,index=None):
    '''Dual of optimization constraint, after the problem is solved.'''
    return constraint[index].dual
def sum_vars(variables): return sum(variables)
def newProblem(): return Problem()
def new_variable(name='',kind='Continuous',low=-1000000,high=1000000):
    '''
    Create an optimization variable.
    :param name: name of optimization variable.
    :param kind: type of variable, specified by string. {Continuous or Binary/Boolean}
    :param low: low limit of variable
    :param high: high limit of variable
    '''
    return pyomo.Var(name=name,bounds=(low,high),domain=variable_kinds[kind])
def new_constraint(name,expression): 
    '''Create an optimization constraint.'''
    return pyomo.Constraint(name=name,rule=expression)


<<<<<<< HEAD
<<<<<<< HEAD
    def solve(problem,solver='cplex'):
        '''solve the optimization problem'''
        logging.info('Solving with {s} ... '.format(s=solver))
<<<<<<< HEAD
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
=======

        if   solver.lower()=='cplex':  out=problem.solve(pulp.CPLEX_CMD(msg=0)),
        elif solver.lower()=='glpk':   out=problem.solve(pulp.GLPK_CMD(msg=0)),
        elif solver.lower()=='gurobi': out=problem.solve(pulp.GUROBI(msg=0))
        elif solver.lower()=='coin':   out=problem.solve(pulp.COINMP_DLL(msg=0))
        else:
            msg='Couldnt find the solver "{}"'.format(solver)
            raise OptimizationError(msg)
>>>>>>> prep. for merge. added coin solver to optimization. added write problem option to solve.
        if problem.status:
            logging.info('{stat} in {time:0.4f} sec'.format(
                stat=problem.statusText(),
                time=problem.solutionTime))
<<<<<<< HEAD
        #else: logging.warning(problem.statusText())
=======
        else: logging.warning(problem.statusText())
>>>>>>> prep. for merge. added coin solver to optimization. added write problem option to solve.
        return out
    def value(variable):
=======
    def value(variable,problem=None):
>>>>>>> working coopr and pulp mix
        '''value of an optimization variable'''
        try: return pulp.value(variable)
        except AttributeError: return variable
    def dual(constraint,index=None):
        return constraint.pi
    def sum_vars(variables):
        '''sums a list of optimization variables'''
        return pulp.lpSum(variables)
    def newProblem(name='problem',kind=pulp.LpMinimize):
        '''create a new problem'''
        return Problem(name=name,sense=kind)
    def new_variable(name='',kind='Continuous',low=-1000000,high=1000000):
        '''create an optimization variable'''
        #note that if binary variable, pulp will reset the bounds to (0,1)
        #note that if using glpk, bounds of -inf and inf produces error
        return pulp.LpVariable(name=name,cat=kind,lowBound=low,upBound=high)
=======
>>>>>>> dropped pulp from optimization module. clean up docstrings.



class OptimizationObject(object):
    '''
    A template for an optimization object. 
    Override the methods of the template with your own.
    '''
    def __init__(self,*args,**kwargs):
        '''
        Individual class defined.
        Initialize the object. Often this just means assigning 
        all of the keyword arguments to self.
        The :meth:`~OptimizationObject.init_optimization` method should be called in __init__.
        '''
        update_attributes(self,locals()) #load in inputs
        self.init_optimization()
        
    def init_optimization(self):
        '''
        Initialize optimization components: add containers for variables, 
        constraints, and an objective component. If the index is not
        defined, make it a hash of the object to ensure the index is unique.
        '''
        self.variables=dict()
        self.constraints=dict()
        self.objective  =0 #cost
<<<<<<< HEAD
        if self.index is None: self.index=hash(self)
        if self.name in [None, '']: self.name = self.index+1 #1 and up naming
=======
        self.children=dict()
        if getattr(self,'index',None) is None: self.index=hash(self)
        if getattr(self,'name',None)=='': self.name = self.index+1 #1 and up naming
>>>>>>> first working pass through solver (results still needs major rework
        
    def create_variables(self, times,*args,**kwargs):
        ''' 
<<<<<<< HEAD
        Here we would create the variables.
        Variables should not belong to the :class:`OptimizationObject` directly, 
        but you can write you own shortcut class methods, 
        like :meth:`~powersystems.Generator.P`.
=======
        Individual class defined.
        Create the variables in this method by using calls to
        :meth:`~optimization.OptimiationObject.add_variable`.
        Variables will be accessible by using
        :meth:`~optimization.OptimiationObject.get_variable` (or by adding
        a shortcut methods, like :meth:`~powersystems.Generator.power`).
>>>>>>> dropped pulp from optimization module. clean up docstrings.
        
        :returns: dictionary of variables belonging to the object and all its children (components)
        '''
        return self.all_variables(times)
    def create_objective(self,times):
        '''
        Individual class defined.
        Create the contribution to the objective (cost) expression.
        :returns: an expression, the default is 0
        '''
        return self.objective
    def create_constraints(self, times,*args,**kwargs):
        ''' 
        Individual class defined.
        Create the constraints in this method by using calls to
        :meth:`~optimization.OptimiationObject.add_constraint`.
        Constraints will be accessible by using
        :meth:`~optimization.OptimiationObject.get_constraint` (or by adding
        a shortcut methods, like :meth:`~powersystems.Bus.price`.
        
        :returns: dictionary of constraints belonging to the object and all its children (components)
        '''
        return self.all_constraints(times)
 
    def update_variables(self):
        '''Replace the object and its children's variables with their numeric value.'''
        for name,var in self.variables.items(): self.variables[name]=value(var)
        for child in self.children.values(): 
            try: child.update_variables()
            except AttributeError:
                for c in child: c.update_variables() 
    def _t_id(self,name,time): return name.replace(' ','_')+'_'+self.iden(time)
    
    def add_variable(self,name,short_name=None,time=None,fixed_value=None,**kwargs):
        '''
        Create a new variable and add it to the variables dictionary.
        Parameters include those for `meth:optimization.new_variable`.
        '''        
        if short_name is None: short_name=name
        name=self._t_id(name,time)
        short_name=self._t_id(short_name,time)
        if fixed_value is None:
            self.variables[name] = new_variable(name=short_name,**kwargs)
        else:
            self.variables[name] = fixed_value

    def add_constraint(self,name,time,expression): 
        '''Create a new constraint and add it to the constraints dictionary.'''
        name=self._t_id(name,time)
        self.constraints[name]=new_constraint(name,expression)

    def get_variable(self,name,time): return self.variables[self._t_id(name,time)]
    def get_constraint(self,name,time): return self.constraints[self._t_id(name,time)]
    
    def add_components(self,objL,name):
        '''Add a child :class:`~optimization.OptimizationObject` to this object.''' 
        self.children[name]=objL 
        setattr(self,name,objL)
    def add_component(self,obj,name,time): 
        '''Add a child :class:`~optimization.OptimizationObject` dependent on time to this object.'''
        self.children[self._t_id(name,time)]=obj    
    def get_component(self,name,time=None): 
        '''Get a child :class:`~optimization.OptimizationObject` dependent on time from this object.'''
        return self.children[self._t_id(name,time)]
    #def get_cost(self,times): return self.objective+sum([child.get_cost(times) for child in self.children])
    def iden(self,time):
        '''
        Individual class defined.
        Identifing string for the object, depending on time. Used to name variables and constraints for the object.  
        '''
        msg='the iden() method must be overwritten for a child of the OptimizationObject class'
        raise NotImplementedError(msg)
        return 'some unique identifying string'
    def __str__(self): 
        '''
        Individual class defined.
        A string representation of the object (used when calling ``print``).
        You probably want to override this one with a more descriptive string.
        '''
        return 'opt_obj{ind}'.format(ind=self.index)
    def all_variables(self,times):
        '''return variables from object and children within times'''
        variables=filter_optimization_objects(self.variables,times)
        for child in self.children.values(): 
            try: variables.update(child.all_variables(times))
            except AttributeError:
                [variables.update(c.all_variables(times)) for c in child]
        return variables
    def all_constraints(self,times): 
        '''return constraints from object and children within times'''
        constraints=filter_optimization_objects(self.constraints,times)
        for child in self.children.values(): 
            try: constraints.update(child.all_constraints(times))
            except AttributeError:
                [constraints.update(c.all_constraints(times)) for c in child]
        return constraints


def filter_optimization_objects(objects,times):
    '''Filter variables or constraints by times.''' 
    times_str=[str(t).lstrip('t') for t in times]
    times_str.append(str(times.initialTime).lstrip('t'))
    def valid(name,val):
        in_time_period=name.rsplit('t',1)[1] in times_str
        is_variable_not_fixed = getattr(val,'value',0)==None
        return in_time_period and is_variable_not_fixed
    return dict(filter(lambda (name,val): valid(name,val) ,objects.items()))


#def solve(problem,solver=config.optimization_solver,problem_filename=False): 
#    '''
#    Solve an optimization problem.
#    :param problem: a :class:`~optimization.Problem` object
#    :param solver: name of solver (lowercase string). Valid solvers are {cplex,gurobi,glpk}.
#    :param problem_filename: write MIP problem formulation to a file, if a file name is specified
#    '''
#    return problem.solve(solver,problem_filename)

class OptimizationError(Exception):
    '''Error that occurs within solving an optimization problem.'''
    def __init__(self, ivalue):
        if ivalue: self.value=ivalue
        else: self.value="Optimization Error: there was a problem"
        Exception.__init__( self, self.value)

    def __str__(self): return self.value
