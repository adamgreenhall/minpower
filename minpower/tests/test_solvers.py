'''Test the all of the solver links'''

from minpower import optimization, config
from test_utils import *
from coopr import pyomo

mem_tracking=False
if mem_tracking:
    from pympler.classtracker import ClassTracker
    from pympler.classtracker_stats import HtmlStats
    import objgraph
    tracker=ClassTracker()
    for cls in [pyomo.ConcreteModel,pyomo.Var,pyomo.base.var._VarElement,pyomo.Constraint,optimization.OptimizationProblem]:
        tracker.track_class(cls)

def simple_problem():
    prob=optimization.OptimizationProblem()
    if mem_tracking: tracker.create_snapshot('prob. init')
    prob.add_variable('x',low=0,high=3)
    prob.add_variable('y',low=0,high=1)
    x=prob.get_component('x')
    y=prob.get_component('y')
    prob.add_objective(y-4*x)
    prob.add_constraint('ineq',x+y<=2)
    if mem_tracking: tracker.create_snapshot('prob. created')
    return prob 


def run_one_solver(solver_name):
    prob=simple_problem()
    orig_solver = config.user_config.solver
    config.user_config.duals = False
    config.user_config.solver = solver_name 
    
    prob.solve()
    if mem_tracking: tracker.create_snapshot('prob. solved')
    status=prob.solved
    del prob
    if mem_tracking: tracker.create_snapshot('prob. deleted')
    if solver_name=='glpk' and mem_tracking:
        tracker.stats.print_summary()
        #HtmlStats(tracker=tracker).create_html('profile-simple-problem.html')
        models_left=objgraph.by_type('ConcreteModel')
        print models_left
        objgraph.show_backrefs(models_left,filename='backrefs-simple-problem.png')
    
    config.user_config.duals = True
    config.user_config.solver = orig_solver
    return status

@istest
def cplex():
    '''Test each available solver on a simple problem'''
    if 'cplex' in config.available_solvers:
        assert run_one_solver('cplex')


@istest
def glpk():
    '''Test the glpk solver on a simple problem'''
    if 'glpk' in config.available_solvers:
        assert run_one_solver('glpk')


@istest
def gurobi():
    '''Test the gurobi solver on a simple problem'''
    if 'gurobi' in config.available_solvers:
        assert run_one_solver('gurobi')        
