"""
Power systems optimization problem solver
for ED, OPF, UC, and SCUC problems. The :mod:`solve`
module contains the top-level commands for creating
problems and solving them.
"""

import logging

from optimization import OptimizationError
import get_data
import powersystems
import results
import config
from commonscripts import joindir,show_clock
    
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
    
    if shell: solution.show()
    if csv: solution.saveCSV()
    if visualization: solution.visualization()
    if solution_file: solution.save(solution_file)
    return solution

def create_solve_problem(power_system,times,datadir,solver,problemfile=False,get_duals=True):
    create_problem(power_system,times)
    if problemfile: problemfile=joindir(datadir,'problem-formulation.lp')
    
    power_system.solve(solver,problem_filename=problemfile,get_duals=get_duals)
    solution=results.make_solution(power_system,times,datadir=datadir)
    
        
    return solution
def create_problem(power_system,times):
    """
    Create an optimization problem.
    
    :param power_system: a :class:`~powersystems.PowerSystem` object
    :param times: :class:`~schedule.Timelist` object
    
    :returns: :class:`~optimization.Problem` object
    """
    
    
    
    logging.debug('initialized problem {}'.format(show_clock()))
    power_system.create_variables(times)
    logging.debug('created variables {}'.format(show_clock()))
    power_system.create_objective(times)
    logging.debug('created objective {}'.format(show_clock()))
    power_system.create_constraints(times)
    logging.debug('created constraints {}'.format(show_clock()))
    return


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
        for gen in power_system.generators():
            gen.finalstatus=gen.getstatus(t=next_stage_first_time,times=times)


    for stg,t_stage in enumerate(stage_times):
        #print 'Stage starting at {}, {}'.format(t_stage[0].Start, show_clock(showclock))
        logging.info('Stage starting at {}, {}'.format(t_stage[0].Start, show_clock(showclock)))
        set_initialconditions(buses,t_stage.initialTime)
        
        try: stage_solution=create_solve_problem(power_system,t_stage,datadir,solver,problemfile,get_duals)
        except OptimizationError:
            #re-do stage, with load shedding allowed
            logging.critical('stage infeasible, re-running with load shedding.')
            power_system.reset_model()
            power_system.set_load_shedding(True)
            try: 
                stage_solution=create_solve_problem(power_system,t_stage,datadir,solver,problemfile=True,get_duals=get_duals)
            except OptimizationError:
                stage_solutions[-1].saveCSV(joindir(datadir,'last-stage-solved-commitment.csv'),save_final_status=True) 
                raise OptimizationError('failed to solve, even with load shedding.')
            power_system.set_load_shedding(False)

        logging.debug('solved... get results... {}'.format(show_clock(showclock)))
        get_finalconditions(power_system,t_stage)
        stage_solutions.append(stage_solution)
        
        if stg<len(stage_times)-1: power_system.reset_model()
    return stage_solutions,stage_times

  
def _setup_logging(level,filename=False):
    ''' set up the logging to report on the status'''
    if filename:
        logging.basicConfig( level=level, format='%(levelname)s: %(message)s',filename=filename)
    else: logging.basicConfig( level=level, format='%(levelname)s: %(message)s')
