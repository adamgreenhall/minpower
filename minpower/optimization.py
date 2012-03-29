"""
An optimization command library for Minpower.
"""
import coopr.pyomo as pyomo
from coopr.opt.base import solvers as cooprsolver

variable_kinds = dict(Continuous=pyomo.Reals, Binary=pyomo.Boolean, Boolean=pyomo.Boolean)

import logging,time
import config
from commonscripts import update_attributes,show_clock

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
        self.children=dict()
        if getattr(self,'index',None) is None: self.index=hash(self)
        if getattr(self,'name',None)=='': self.name = self.index+1 #1 and up naming
        
    def create_variables(self, times,*args,**kwargs):
        ''' 
        Individual class defined.
        Create the variables in this method by using calls to
        :meth:`~optimization.OptimiationObject.add_variable`.
        Variables will be accessible by using
        :meth:`~optimization.OptimiationObject.get_variable` (or by adding
        a shortcut methods, like :meth:`~powersystems.Generator.power`).
        
        :returns: dictionary of variables belonging to the object and all its children (components)
        '''
        return self.all_variables(times)
    def create_objective(self,times):
        '''
        Individual class defined.
        Return the contribution to the objective (cost) expression.
        :returns: an expression, the default is 0
        '''
        return 0
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
        for name,var in self.variables.items(): 
            self.variables[name]=value(var)
            try: var._varval=[]
            except AttributeError: pass
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

    def get_variable(self,name,time): 
        try: return self.variables[self._t_id(name,time)]
        except KeyError:
            print self.variables.keys()
            raise
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
        variables=self.variables
        for child in self.children.values(): 
            try: variables.update(child.all_variables(times))
            except AttributeError:
                [variables.update(c.all_variables(times)) for c in child]
        return variables
    def all_constraints(self,times): 
        '''return constraints from object and children within times'''
        constraints=self.constraints
        for child in self.children.values(): 
            try: constraints.update(child.all_constraints(times))
            except AttributeError:
                [constraints.update(c.all_constraints(times)) for c in child]
        return constraints
    def clear_constraints(self):
        self.constraints={}
        for child in self.children.values(): 
            try: child.clear_constraints()
            except AttributeError:
                #child is a list of objects
                for c in child: c.clear_constraints()


class OptimizationProblem(OptimizationObject):
    '''an optimization problem/model based on pyomo'''
    def __init__(self):
        self.init_optimization()
    def init_optimization(self):
        self._model=pyomo.ConcreteModel('power system problem')
        self.solved=False
        self.children=dict()
        self.variables=dict()
        self.constraints=dict()
    def add_objective(self,expression,sense=pyomo.minimize):
        '''add an objective to the problem'''            
        self._model.objective=pyomo.Objective(name='objective',rule=expression,sense=sense)
    def add_variable(self,variable):
        '''add a single variable to the problem'''
        try: self._model._add_component(variable.name,variable)
        except AttributeError: pass #just a number, don't add to vars
    def add_constraint(self,constraint):
        '''add a single constraint to the problem'''
        self._model._add_component(constraint.name,constraint)
    def write_model(self,filename): self._model.write(filename)
    def solve(self,solver=config.optimization_solver,problem_filename=False,get_duals=True):
        '''
        Solve the optimization problem.
        
        :param solver: name of solver (lowercase string).
        :param problem_filename: write MIP problem formulation to a file, if a file name is specified
        :param get_duals: get the duals, or prices, of the optimization problem
        '''
        
        current_log_level = logging.getLogger().getEffectiveLevel()      
                    
        def cooprsolve(instance,suffixes=['dual'],keepFiles=False):
            if not keepFiles: logging.getLogger().setLevel(logging.WARNING) 
            opt_solver = cooprsolver.SolverFactory(solver)
            if opt_solver is None: 
                msg='solver "{}" not found'.format(solver)
                raise OptimizationError(msg)
            start = time.time()
            results= opt_solver.solve(instance,suffixes=suffixes) #,keepFiles=keepFiles
            try: opt_solver._symbol_map=None #this should mimic the memory leak bugfix at: software.sandia.gov/trac/coopr/changeset/5449
            except AttributeError: pass      #should remove after this fix becomes part of a release 
            elapsed = (time.time() - start)
            logging.getLogger().setLevel(current_log_level)
            return results,elapsed
        
        
        logging.info('Solving with {s} ... {t}'.format(s=solver,t=show_clock()))
        instance=self._model.create()
        logging.debug('... model created ... {t}'.format(t=show_clock()))     
        
        results,elapsed=cooprsolve(instance,suffixes=[])
        
        status_text = str(results.solver[0]['Termination condition'])
        if (not status_text =='optimal' and solver!='cbc') or status_text=='infeasible':
            logging.critical('problem not solved. Solver terminated with status: "{}"'.format(status_text))
            self.solved=False
        else:
            self.solved=True
            self.solution_time =elapsed #results.Solver[0]['Wallclock time']
            logging.info('Problem solved in {}s.'.format(self.solution_time))
            logging.debug('... {t}'.format(t=show_clock()))
        
        if problem_filename:
            logging.disable(logging.CRITICAL) #disable coopr's funny loggings when writing lp files.  
            self.write_model(problem_filename)
            logging.disable(current_log_level)
                
        if not self.solved: 
            self.write_model('unsolved-problem-formulation.lp')
            OptimizationError('problem not solved')
        
        instance.load(results)
#        instance._load_solution(results.solution(0), ignore_invalid_labels=True )
        logging.debug('... solution loaded ... {t}'.format(t=show_clock()))

        
        def resolvefixvariables(instance,results):
            active_vars= instance.active_components(pyomo.Var)
            for var in active_vars.values():
                if isinstance(var.domain, pyomo.base.IntegerSet) or isinstance(var.domain, pyomo.base.BooleanSet): var.fixed=True
            
            logging.info('resolving fixed-integer LP for duals')
            instance.preprocess()
            try:
                results,elapsed=cooprsolve(instance,suffixes=['dual'])
                self.solution_time+=elapsed
            except RuntimeError:
                logging.error('coopr raised an error in solving. keep the files for debugging.')
                results= cooprsolve(instance, keepFiles=True)    
            
            instance.load(results)
            return instance,results

        if get_duals: 
            try: instance,results = resolvefixvariables(instance,results)
            except RuntimeError:
                logging.error('in re-solving for the duals. the duals will be set to default value.')
            logging.debug('... LP problem solved ... {t}'.format(t=show_clock()))    
                
        try: self.objective = results.Solution.objective['objective'].value #instance.active_components(pyomo.Objective)['objective']
        except AttributeError:
            self.objective = results.Solution.objective['__default_objective__'].value
            
        self.constraints = instance.active_components(pyomo.Constraint)
        self.variables =   instance.active_components(pyomo.Var)

        return 

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






class OptimizationError(Exception):
    '''Error that occurs within solving an optimization problem.'''
    def __init__(self, ivalue):
        if ivalue: self.value=ivalue
        else: self.value="Optimization Error: there was a problem"
        Exception.__init__( self, self.value)

    def __str__(self): return self.value
