"""
An optimization command library for Minpower.
"""
import coopr.pyomo as pyomo
from coopr.opt.base import solvers as cooprsolver

pyomo.base.numvalue.KnownConstants[True]=pyomo.base.numvalue.NumericConstant(None, None, 1.0)

variable_kinds = dict(Continuous=pyomo.Reals, Binary=pyomo.Boolean, Boolean=pyomo.Boolean)

import logging,time,weakref

import config
from commonscripts import update_attributes,show_clock

class OptimizationObject(object):
    '''
    A base class for an optimization object. 
    This also serves as a template for how :class:`~OptimizationObject`s are structured.
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
        Initialize optimization components: add a container for children.
        If the index is not defined, make it a hash of the object to ensure the index is unique.
        '''
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
        '''
        return #self.all_variables(times)
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
        '''
        return #self.all_constraints(times)
 
    def _t_id(self,name,time): return name.replace(' ','_')+'_'+self.iden(time)
    def _id(self,name): return name.replace(' ','_')+'_'+str(self)
    
    def add_variable(self,name,time=None,fixed_value=None,index=None,**kwargs):
        '''
        Create a new variable and add it to the object's variables and the model's variables.
        :param name: name of optimization variable.
        :param kind: type of variable, specified by string. {Continuous or Binary/Boolean}
        :param low: low limit of variable
        :param high: high limit of variable
        :param fixed_value: a fixed value for a variable (making it a parameter)
        :param time: a single time for a variable
        :param index: a :class:`pyomo.Set` over which a variable is created
        '''
        def map_args(kind='Continuous',low=None,high=None): return dict(bounds=(low,high),domain=variable_kinds[kind]) 
        orig_name=name
        if index is None:
            name=self._t_id(name,time)
            if fixed_value is None:
                var=pyomo.Var(name=name, **map_args(**kwargs)) #new_variable(name=short_name,**kwargs)
                self._parent_problem().add_component_to_problem(var)
            else:
                var=pyomo.Param(name=name,default=fixed_value)
                #add var
                self._parent_problem().add_component_to_problem(var)
                #and set value
                var=self.get_variable(orig_name,time)
                var[None]=fixed_value
        else:
            name=self._id(name)

            if fixed_value is None: 
                var=pyomo.Var(index,name=name,**map_args(**kwargs))
                self._parent_problem().add_component_to_problem(var)
            else: 
                var=pyomo.Param(index,name=name,default=fixed_value)
                self._parent_problem().add_component_to_problem(var)
                var=self._parent_problem().get_component(name)
                for i in index: var[i]=fixed_value
        
            


    def add_parameter(self,name,index=None,default=None):
        name=self._id(name)
        self._parent_problem().add_component_to_problem(pyomo.Param(index,name=name,default=default))
        
    def add_constraint(self,name,time,expression): 
        '''Create a new constraint and add it to the object's constraints and the model's constraints.'''
        name=self._t_id(name,time)
        self._parent_problem().add_component_to_problem(new_constraint(name,expression))
        
    def get_variable(self,name,time=None,indexed=False):
        if indexed: 
            var_name=self._id(name)
            if time is None: 
                return self._parent_problem().get_component(var_name)
            else: 
                index=str(time)
                try: return self._parent_problem().get_component(var_name)[index]
                except KeyError:
                    self._parent_problem().show_model()
                    raise
        else: 
            var_name=self._t_id(name,time)
            return self._parent_problem().get_component(var_name)
    
    def get_constraint(self,name,time): return self._parent_problem().get_component(self._t_id(name,time))
    
    def add_children(self,objects,name):
        '''Add a child :class:`~optimization.OptimizationObject` to this object.''' 
        self.children[name]=objects
        try: 
            #if objects is actually a dictionary
            for child in self.children[name].values(): child._parent_problem=self._parent_problem
        except AttributeError:
            for child in self.children[name]: child._parent_problem=self._parent_problem

        setattr(self,name,objects)        
    # def add_component(self,obj):
    #     obj._parent_problem=self._parent_problem
    #     self.children[obj.name]=obj
        
        
    def get_child(self,name,time=None): 
        '''Get a child :class:`~optimization.OptimizationObject` dependent on time from this object.'''
        try: 
            if time is None: return self.children[name]
            else: return self.children[name][time] 
        except KeyError: 
            print self.children.keys()
            raise
    #def get_cost(self,times): return self.objective+sum([child.get_cost(times) for child in self.children])
    def iden(self,time):
        '''
        Individual class defined.
        Identifing string for the object, depending on time. Used to name variables and constraints for the object.  
        '''
        msg='the iden() method must be overwritten for a child of the OptimizationObject class. this one is '+str(type(self))
        raise NotImplementedError(msg)
        return 'some unique identifying string'
    def __str__(self): 
        '''
        Individual class defined.
        A string representation of the object (used when calling ``print``).
        You probably want to override this one with a more descriptive string.
        '''
        return 'opt_obj{ind}'.format(ind=self.index)
    # def all_variables(self,times):
    #     '''return variables from object and children within times'''
    #     variables=self.variables
    #     for child in self.children.values(): 
    #         try: variables.update(child.all_variables(times))
    #         except AttributeError:
    #             [variables.update(c.all_variables(times)) for c in child]
    #     return variables
    # def all_constraints(self,times): 
    #     '''return constraints from object and children within times'''
    #     constraints=self.constraints
    #     for child in self.children.values(): 
    #         try: constraints.update(child.all_constraints(times))
    #         except AttributeError:
    #             [constraints.update(c.all_constraints(times)) for c in child]
    #     return constraints
    # def clear_constraints(self):
    #     self.constraints={}
    #     for child in self.children.values(): 
    #         try: child.clear_constraints()
    #         except AttributeError:
    #             #child is a list of objects
    #             for c in child: c.clear_constraints()


class OptimizationProblem(OptimizationObject):
    '''an optimization problem/model based on pyomo'''
    def __init__(self):
        self.init_optimization()
    def init_optimization(self):
        self._model=pyomo.ConcreteModel('power system problem')
        self.stochastic_formulation=False
        self.solved=False
        self.children=dict()
        self.variables=dict()
        self.constraints=dict()
    def add_children(self,objL,name):
        '''Add a child :class:`~optimization.OptimizationObject` to this object.''' 
        self.children[name]=objL
        setattr(self,name,objL)
        for child in self.children[name]:
            child._parent_problem=weakref.ref(self)

    def add_component_to_problem(self,component):
        '''add a optimization component to the model'''
        self._model._add_component(component.name,component)
    def add_objective(self,expression,sense=pyomo.minimize):
        '''add an objective to the problem'''            
        self._model.objective=pyomo.Objective(name='objective',rule=expression,sense=sense)
    def add_set(self,name,items):         
        '''add a :class:`pyomo.Set` to the problem'''
        self._model._add_component(name,pyomo.Set(initialize=items,name=name))
    def add_variable(self,name,**kwargs):
        '''create a new variable and add it to the root problem'''
        def map_args(kind='Continuous',low=None,high=None): return dict(bounds=(low,high),domain=variable_kinds[kind]) 
        var=pyomo.Var(name=name, **map_args(**kwargs))
        self._model._add_component(name,var)
    def add_constraint(self,name,expression):
        self._model._add_component(name,new_constraint(name,expression))
    def get_component(self,name): 
        '''Get an optimization component'''
        try: return getattr(self._model,name)
        except AttributeError:
            print 'error getting ',name
            self.show_model()
            raise 

    def write_model(self,filename): self._model.write(filename)
    def reset_model(self):
        #piecewise models leak memory
        #keep until Coopr release integrates: https://software.sandia.gov/trac/coopr/changeset/5781 
        for pw in self._model.active_components(pyomo.Piecewise).values():
            pw._constraints_dict=None
            pw._vars_dict=None
            pw._sets_dict=None
        
        self._model=None
        self.solved=False
        self._model=pyomo.ConcreteModel() 
    def show_model(self):
        components=self._model.components._component
        items = [pyomo.Set, pyomo.Param, pyomo.Var, pyomo.Objective, pyomo.Constraint]
        for item in items:
            if not item in components: continue
            keys = components[item].keys()
            keys.sort()
            print len(keys), item.__name__+" Declarations"
            for key in keys: components[item][key].pprint()
            print ""
    def update_variables(self):
        '''Replace the variables with their numeric value.'''
        for name,var in self._model.active_components(pyomo.Var).items(): 
            try: setattr(self._model,name,value(var))
            except ValueError: 
                #for boolean sets this doesnt work due to rounding
                if var.domain==pyomo.Boolean:
                    setattr(self._model,name,int(value(var)))
                else: raise
                
            
    def solve(self,solver=config.optimization_solver,problem_filename=False,get_duals=True):
        '''
        Solve the optimization problem.
        
        :param solver: name of solver (lowercase string).
        :param problem_filename: write MIP problem formulation to a file, if a file name is specified
        :param get_duals: get the duals, or prices, of the optimization problem
        '''
                    
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
            logging.getLogger().setLevel(config.logging_level)
            return results,elapsed
        
        
        logging.info('Solving with {s} ... {t}'.format(s=solver,t=show_clock()))
        if self.stochastic_formulation:
            instance=self._stochastic_instance
        else: 
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
            logging.getLogger().setLevel(logging.CRITICAL) #disable coopr's funny loggings when writing lp files.  
            self.write_model(problem_filename)
            logging.getLogger().setLevel(config.logging_level)
                
        if not self.solved: 
            self.write_model('unsolved-problem-formulation.lp')
            raise OptimizationError('problem not solved')
        
        instance.load(results)
#        instance._load_solution(results.solution(0), ignore_invalid_labels=True )
        logging.debug('... solution loaded ... {t}'.format(t=show_clock()))

        
        def resolvefixvariables(instance,results):
            active_vars= instance.active_components(pyomo.Var)
            for var in active_vars.values():
                if isinstance(var.domain, pyomo.base.IntegerSet) or isinstance(var.domain, pyomo.base.BooleanSet): 
                    if var.is_indexed(): 
                        for key,ind_var in var.iteritems(): ind_var.fixed=True
                    else: var.fixed=True
            
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
        
        def get_objective(name):
            try: return results.Solution.objective[name].value
            except AttributeError: return results.Solution.objective['objective'].value
        obj_name='__default_objective__'
        #if self.stochastic_formulation and not get_duals: obj_name='MASTER'
        #print results.Solution.objective
        #print get_duals,self.stochastic_formulation,obj_name
        self.objective = get_objective(obj_name)
        
        #self.constraints = instance.active_components(pyomo.Constraint)
        #self.variables =   instance.active_components(pyomo.Var)

        return 
    def __str__(self): return 'power_system_problem'

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

def new_variable(name='',kind='Continuous',low=None,high=None):
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
