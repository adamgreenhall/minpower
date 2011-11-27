"""
Power systems optimization problem solver
for ED, OPF, UC, and SCUC problems. The :mod:`solve`
module contains the top-level commands for creating
problems and solving them.
"""

import objgraph,inspect,random
#import weakref
#import memory_size
from pympler.asizeof import asizeof
from pympler import summary,muppy
from pympler.classtracker import ClassTracker
from pympler.classtracker_stats import HtmlStats
from pympler.refgraph import ReferenceGraph
from pympler import refbrowser
import coopr.pyomo as pyomo
import bidding,schedule

import yaml

import logging,subprocess

import optimization
import get_data
import powersystems
import results
import config
from commonscripts import joindir,show_clock

tracker = ClassTracker()
tracker_all=ClassTracker()
tracker_gens = ClassTracker()


def problem(datadir='.',
        shell=True,
        problemfile=False,
        visualization=True,
        csv=True,
        solver=config.optimization_solver,
        num_breakpoints=config.default_num_breakpoints,
        hours_commitment=config.default_hours_commitment,
        hours_commitment_overlap=config.default_hours_commitment_overlap,
        get_duals=True,
        dispatch_decommit_allowed=False,
        logging_level=config.logging_level,
        logging_file=False,
        ):
    """ 
    Solve a optimization problem specified by spreadsheets in a directory.
    Read in data, create and solve the problem, and return solution.
    The problem type is determined by the data.
        
    :param datadir: directory of data files, see :mod:`get_data`
    :param shell: output solution information to the command line
    :param problemfile: write the problem formulation to a problem-formulation.lp file
    :param visualization: create a visualization of the solution and save it to a file
    :param csv: create a spreadsheet of the solution
    :param solver: choice of solver, a lowercase string
    :param num_breakpoints: number of break points to use in linearization of bid (or cost) polynomials (equal to number of segments + 1)
    :param hours_commitment: maximum length of a single unit commitment, times beyond this will be divided into multiple problems and solved in a rolling commitment
    :param hours_commitment_overlap: overlap of commitments for rolling commitments
    :param get_duals: get the duals, or prices, of the optimization problem
    :param dispatch_decommit_allowed: allow de-commitment of units in an ED -- useful for getting initial conditions for UCs  
    :returns: :class:`~results.Solution` object
    """
    
    for cls in [powersystems.PowerSystem,powersystems.Generator,
                pyomo.ConcreteModel,pyomo.Var,pyomo.base.var._VarElement,
                pyomo.Constraint,
                bidding.Bid,results.Solution,results.Solution_UC_multistage,
                optimization.Problem,schedule.Timelist
                ]:
        tracker_all.track_class(cls)
    
    _setup_logging(logging_level,logging_file)
    logging.debug('Minpower reading {} {}'.format(datadir, show_clock()))
    generators,loads,lines,times=get_data.parsedir(datadir)
    tracker_all.create_snapshot('data read')
    logging.debug('data read {}'.format(show_clock()))
    power_system=powersystems.PowerSystem(generators,loads,lines,                 
                num_breakpoints=num_breakpoints,
                load_shedding_allowed=False,
                #spinning_reserve_requirement=0,
                dispatch_decommit_allowed=dispatch_decommit_allowed,)
    tracker_all.create_snapshot('power system created')
    logging.debug('power system set up {}'.format(show_clock()))
    
    if times.spanhrs<=hours_commitment:
        solution=create_solve_problem(power_system,times,datadir,solver,problemfile,get_duals)
        tracker_all.create_snapshot('solution returned')
    else: #split into multiple stages and solve
        stage_solution_files,stage_times=solve_multistage_standalone(power_system,times,datadir,
                                                       solver=solver,
                                                       get_duals=get_duals,
                                                       stage_hours=hours_commitment,
                                                       overlap_hours=hours_commitment_overlap,
                                                       )
        solution=results.make_multistage_solution_standalone(power_system,stage_times,datadir,stage_solution_files)
#        tracker.create_snapshot('solution created')
        logging.info('problem solved in {} ... finished at {}'.format(solution.solve_time,show_clock()))
        tracker_all.create_snapshot('all times solution created')
#        gb = ReferenceGraph([power_system,times,solution])
#        gb.render('mutlistage-memory.png',format='png')
    tracker_all.stats.print_summary()
#    tracker_all.stats.dump_stats('pympler.stats')
#    stats = HtmlStats()
#    stats.load_stats('pympler.stats')
#    stats.create_html('profile-memory.html')

#    tracker_gens.stats.print_summary()
#    tracker_all.stats.print_summary()
    HtmlStats(tracker=tracker_all).create_html('profile.html')

#    print 'testing refbrowser'
#    obj='the object im testing'
#    stuff=[obj]
#    stuffer={obj:'abc'}
#    def output_function(o): return str(type(o))
#    cb=refbrowser.ConsoleBrowser(obj, str_func=output_function, maxdepth=2)
#    print cb
#    cb.print_tree()       
    if shell: solution.show()
    if csv: solution.saveCSV()
    if visualization: solution.visualization()
    return solution

def create_solve_problem(power_system,times,datadir,solver,problemfile=False,get_duals=True):
    problem=create_problem(power_system,times)
    if problemfile: problemfile=joindir(datadir,'problem-formulation.lp')
    problem.solve(solver,problem_filename=problemfile,get_duals=get_duals)
    
    if problem.solved:
        solution=results.make_solution(power_system,times,problem=problem,datadir=datadir)
    else: 
        raise optimization.OptimizationError('problem not solved')
    return solution
def create_problem(power_system,times):
    """
    Create an optimization problem.
    
    :param power_system: a :class:`~powersystems.PowerSystem` object
    :param times: :class:`~schedule.Timelist` object
    
    :returns: :class:`~optimization.Problem` object
    """
    
    
    prob=optimization.newProblem()
    logging.debug('initialized problem {}'.format(show_clock()))
    variables =power_system.create_variables(times)
    logging.debug('created variables {}'.format(show_clock()))
    objective=power_system.create_objective(times)
    logging.debug('created objective {}'.format(show_clock()))
    constraints=power_system.create_constraints(times)
    logging.debug('created constraints {}'.format(show_clock()))
    
    tracker_all.create_snapshot('power system problem created')
    for v in variables.values(): prob.add_variable(v)
    for c in constraints.values(): prob.add_constraint(c)
    prob.add_objective(objective)
    
#    print 'variable type is', type(v)
#    print 'objective type is', type(objective)
    #objgraph.show_backrefs([v], filename='variable-backref-pre-solve.png')
    tracker_all.create_snapshot('Problem created')
    return prob

def solve_multistage_standalone(power_system,times,datadir,
                              solver=config.optimization_solver,
                              interval_hours=None,
                              stage_hours=config.default_hours_commitment,
                              overlap_hours=config.default_hours_commitment_overlap,
                              writeproblem=False,
                              get_duals=True,
                              showclock=True):
    if not interval_hours: interval_hours=times.intervalhrs
        
    stage_times=times.subdivide(hrsperdivision=stage_hours,hrsinterval=interval_hours,overlap_hrs=overlap_hours)
    stage_solution_files=[]
    times_file='/tmp/uc-rolling-times.yaml'
    init_file='/tmp/uc-rolling-init.yaml' 
    power_system_file='/tmp/uc-rolling-power-system.yaml'
    for gen in power_system.generators(): gen.cost_model=None
    with open(power_system_file,'w+') as f: yaml.dump(power_system,f)
    def call_solve_standalone(stage_solution_file):
        inputs=dict(
            solution_file=stage_solution_file,
            power_system_file=power_system_file,
            times_file=times_file,
            init_file=init_file,
            solver=solver,
            data_dir=datadir,
#            num_breakpoints=10,
            )
        input_args=''.join(['--{k} {v} '.format(k=k,v=v) for k,v in inputs.items()])
        subprocess.check_call('solve_standalone_minpower '+input_args,shell=True)
    
    ti=times.initialTime
    init_statuses=[dict(P=gen.power(ti),u=gen.status(ti),hoursinstatus=getattr(gen,'initialStatusHours',0)) for gen in power_system.generators()]
    
    with open(init_file,'w+') as f: yaml.dump(init_statuses,f)
    for n,t_stage in enumerate(stage_times):    
        logging.info('stage {} started ... finished at {}'.format(t_stage[0].Start,show_clock()))
        #write stage times
        with open(times_file,'w+') as f: yaml.dump(t_stage,f)
        #solve the problem
        stage_solution_file='/tmp/uc-rolling-stage{n}.yaml'.format(n=n)
        call_solve_standalone(stage_solution_file)
        stage_solution_files.append(stage_solution_file)
        logging.info('stage {} solved ... finished at {}'.format(t_stage[0].Start,show_clock()))
        
    return stage_solution_files,stage_times

def _setup_logging(level,filename=False):
    ''' set up the logging to report on the status'''
    if filename:
        logging.basicConfig( level=level, format='%(levelname)s: %(message)s',filename=filename)
    else: logging.basicConfig( level=level, format='%(levelname)s: %(message)s')
