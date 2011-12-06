"""
Power systems optimization problem solver
for ED, OPF, UC, and SCUC problems. The :mod:`solve`
module contains the top-level commands for creating
problems and solving them.
"""

import logging

from optimization import OptimizationError,Problem
import get_data
import powersystems
import results
import config
from commonscripts import joindir,show_clock

import objgraph,inspect,random
from pympler.classtracker import ClassTracker
from pympler.classtracker_stats import HtmlStats

from coopr import pyomo
from coopr.opt.base.solvers import IOptSolver,OptSolver

profile_memory=False
tracker=ClassTracker()
if profile_memory:
    for cls in [pyomo.ConcreteModel,pyomo.Var,pyomo.base.var._VarElement,
                pyomo.Constraint,Problem,
                IOptSolver,OptSolver,
                ]:
        tracker.track_class(cls)

def show_backref_chain(name):
    try: objgraph.show_chain(objgraph.find_backref_chain( random.choice(objgraph.by_type(name)),inspect.ismodule),filename='{}-chain.png'.format(name))
    except: print 'couldnt find a reference to {} -- skip plotting'.format(name)
def show_backrefs(name):
    try: objgraph.show_backrefs(random.choice(objgraph.by_type(name)),filename='{}-backrefs.png'.format(name))
    except: print 'no objects of type {} -- skipping plotting'.format(name)
    
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
        solution_file=False,
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
    
    _setup_logging(logging_level,logging_file)
    logging.debug('Minpower reading {} {}'.format(datadir, show_clock()))
    generators,loads,lines,times=get_data.parsedir(datadir)
    logging.debug('data read {}'.format(show_clock()))
    power_system=powersystems.PowerSystem(generators,loads,lines,                 
                num_breakpoints=num_breakpoints,
                load_shedding_allowed=False,
                #spinning_reserve_requirement=0,
                dispatch_decommit_allowed=dispatch_decommit_allowed,)
    
    logging.debug('power system set up {}'.format(show_clock()))
    
    tracker.create_snapshot('prob. created')
    
    if times.spanhrs<=hours_commitment:
        solution=create_solve_problem(power_system,times,datadir,solver,problemfile,get_duals)
    else: #split into multiple stages and solve
        stage_solutions,stage_times=solve_multistage(power_system,times,datadir,
                                                       solver=solver,
                                                       get_duals=get_duals,
                                                       stage_hours=hours_commitment,
                                                       overlap_hours=hours_commitment_overlap,
                                                       problemfile=problemfile,
                                                       )
        solution=results.make_multistage_solution(power_system,stage_times,datadir,stage_solutions)
        logging.info('problem solved in {} ... finished at {}'.format(solution.solve_time,show_clock()))
    
    tracker.create_snapshot('solutions solved')
    
    if shell: solution.show()
    if csv: solution.saveCSV()
    if visualization: solution.visualization()
    if solution_file: solution.save(solution_file)
    if profile_memory:
        HtmlStats(tracker=tracker).create_html('profile.html')
        #show_backref_chain('_VarElement')
        #show_backrefs('_VarElement')
    return solution

def create_solve_problem(power_system,times,datadir,solver,problemfile=False,get_duals=True):
    problem=create_problem(power_system,times)
    if problemfile: problemfile=joindir(datadir,'problem-formulation.lp')
    problem.solve(solver,problem_filename=problemfile,get_duals=get_duals)
    
    if problem.solved:
        solution=results.make_solution(power_system,times,problem=problem,datadir=datadir)
    else: 
        raise OptimizationError('problem not solved')
    return solution
def create_problem(power_system,times):
    """
    Create an optimization problem.
    
    :param power_system: a :class:`~powersystems.PowerSystem` object
    :param times: :class:`~schedule.Timelist` object
    
    :returns: :class:`~optimization.Problem` object
    """
    
    
    prob=Problem()
    logging.debug('initialized problem {}'.format(show_clock()))
    variables =power_system.create_variables(times)
    logging.debug('created variables {}'.format(show_clock()))
    objective=power_system.create_objective(times)
    logging.debug('created objective {}'.format(show_clock()))
    constraints=power_system.create_constraints(times)
    logging.debug('created constraints {}'.format(show_clock()))
    for v in variables.values(): prob.add_variable(v)
    for c in constraints.values(): prob.add_constraint(c)
    prob.add_objective(objective)
    return prob

def solve_multistage(power_system,times,datadir,
                              solver=config.optimization_solver,
                              interval_hours=None,
                              stage_hours=config.default_hours_commitment,
                              overlap_hours=config.default_hours_commitment_overlap,
                              problemfile=False,
                              get_duals=True,
                              showclock=True):
    """
    Solve a rolling or multi-stage power systems optimization problem.
    Each stage will be one optimization run. A stage's final
    conditions will be the next stage's initial condition.
    
    :param power_system: :class:`~powersystems.PowerSystem` object
    :param datadir: directory of spreadsheets 
    :param times: :class:`~schedule.Timelist` object. Will be split up into stages
    :param interval_hours: number of hours per interval
    :param stage_hours: number of hours per stage (e.g. run one commitment every stage_hours)
    :param overlap_hours: number of hours that stages overlap (e.g. run a 36hr commitment every 24hrs)
    :param writeproblem: save the formulation of each stage to a file
    :param get_duals: get the duals, or prices, of the optimization problem 
    :param showclock: show the current system time at the start of each stage
    
    :returns: a list of :class:`~results.Solution_UC` objects (one per stage)
    :returns: a list of :class:`~schedule.Timelist` objects (one per stage)
    
    """
        
    if not interval_hours: interval_hours=times.intervalhrs
        
    stage_times=times.subdivide(stage_hours,interval_hrs=interval_hours,overlap_hrs=overlap_hours)
    buses=power_system.buses
    stage_solutions=[]

    
    def set_initialconditions(buses,initTime):
        for bus in buses:
            for gen in bus.generators:
                try: 
                    gen.set_initial_condition(time=initTime,**gen.finalstatus)
                    del gen.finalstatus
                except AttributeError: pass #first stage of problem already has initial time defined

    def get_finalconditions(power_system,times):
        t_back=overlap_hours/times.intervalhrs
        next_stage_first_time = times[-1-int(t_back)]         
        for bus in power_system.buses:
            for gen in bus.generators:
                gen.update_variables()
                gen.finalstatus=gen.getstatus(t=next_stage_first_time,times=times)


    for t_stage in stage_times:
        logging.info('Stage starting at {}, {}'.format(t_stage[0].Start, show_clock(showclock)))
        tracker.create_snapshot('stage started {}'.format(t_stage[0].Start))
        set_initialconditions(buses,t_stage.initialTime)
        
        logging.info('created... solving... {}'.format(show_clock(showclock)))
        try: stage_solution=create_solve_problem(power_system,t_stage,datadir,solver,problemfile,get_duals)
        except OptimizationError:
            #re-do stage, with load shedding allowed
            logging.critical('Stage infeasible, re-running with load shedding.')
            power_system.set_load_shedding(True)
            #save problem formulation for degbugging in case of infeasibility
            stage_solution=create_solve_problem(power_system,t_stage,datadir,solver,problemfile=True,get_duals=get_duals)
            power_system.set_load_shedding(False)
#        else: 
#            #print stage_problem.status,stage_problem.statusText()
#            stage_problem.write('infeasible-problem.lp')
#            try: stage_sln.saveCSV('last-stage-solved.csv')
#            except: logging.critical('could not write last stage solution to spreadsheet')
#            msg='Infeasible problem - writing to .lp file for examination.'
#            raise optimization.OptimizationError(msg)
            


        logging.debug('solved... get results... {}'.format(show_clock(showclock)))
        get_finalconditions(power_system,t_stage)
        stage_solutions.append(stage_solution)
        #tracker.create_snapshot('stage finished {}'.format(t_stage[0].Start))
    return stage_solutions,stage_times

  
def _setup_logging(level,filename=False):
    ''' set up the logging to report on the status'''
    if filename:
        logging.basicConfig( level=level, format='%(levelname)s: %(message)s',filename=filename)
    else: logging.basicConfig( level=level, format='%(levelname)s: %(message)s')
