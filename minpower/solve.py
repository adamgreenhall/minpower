"""
Power systems optimization problem solver
for ED, OPF, UC, and SCUC problems. The :mod:`solve`
module contains the top-level commands for creating
problems and solving them.
"""

import logging
import time as timer

from optimization import OptimizationError
import config, get_data, powersystems, stochastic, results
from commonscripts import * # joindir,show_clock
from config import user_config

def solve_problem(datadir='.',
        shell=True,
        problemfile=False,
        csv=True,
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

    _setup_logging()
    start_time = timer.time()
    logging.debug('Minpower reading {} {}'.format(datadir, show_clock()))
    generators,loads,lines,times,scenario_tree=get_data.parsedir()
    logging.debug('data read {}'.format(show_clock()))
    power_system=powersystems.PowerSystem(generators,loads,lines)
                #spinning_reserve_requirement=0

    logging.debug('power system set up {}'.format(show_clock()))
    if times.spanhrs <= user_config.hours_commitment + user_config.hours_commitment_overlap:
        solution, instance = create_solve_problem(power_system, times, scenario_tree=scenario_tree)
    else: #split into multiple stages and solve
        stage_solutions,stage_times=solve_multistage(power_system, times, scenario_tree=scenario_tree)
        solution=results.make_multistage_solution(power_system, stage_times, stage_solutions)

    if shell: solution.show()
    if csv: solution.saveCSV()
    if user_config.visualization: solution.visualization()
    # if solution_file: solution.save(solution_file)
    logging.info('total time: {}s'.format(timer.time()-start_time))
    return solution

def create_solve_problem(power_system, times, scenario_tree=None,
    multistage=False, stage_number=None, rerun=False):

    if user_config.problemfile: user_config.problemfile = joindir(directory, 'problem-formulation.lp')

    create_problem(power_system,times)

    stochastic_formulation = False
    if scenario_tree is not None and not rerun:
        if multistage: # multiple time stages
            gen = filter(lambda gen: getattr(gen, 'has_scenarios',False) , power_system.generators())[0]
            day_start = times[0].Start
            tree = stochastic.construct_simple_scenario_tree( gen.scenario_values[day_start]['probability'].values.tolist(), time_stage=stage_number )
            logging.debug('constructed tree for stage %i'%stage_number)
        else: tree = scenario_tree
        stochastic_formulation = True
        stochastic.define_stage_variables(tree,power_system,times)
        power_system = stochastic.create_problem_with_scenarios(power_system,times, tree, user_config.hours_commitment, user_config.hours_commitment_overlap)

    instance = power_system.solve(user_config)

    # if stochastic_formulation:
    #     power_system.scenario_tree=scenario_tree
    #     power_system.scenario_instances=scenario_instances

    solution=results.make_solution(power_system,times,datadir=user_config.directory)

    return solution, instance
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


def solve_multistage(power_system, times, scenario_tree):
#    datadir,
#  solver=config.optimization_solver,
#  interval_hours=None,
#  stage_hours=config.default_hours_commitment,
#  overlap_hours=config.default_hours_commitment_overlap,
#                              scenario_tree=None,
#  problemfile=False,
#  get_duals=True,
#                              showclock=True):
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

    if not user_config.interval_hours: interval_hours=times.intervalhrs

    stage_times=times.subdivide(user_config.hours_commitment, interval_hrs=interval_hours, overlap_hrs=user_config.hours_commitment_overlap)
    buses=power_system.buses
    stage_solutions=[]
    
    Nstages = len(stage_times)

    for stg,t_stage in enumerate(stage_times):
        logging.info('Stage starting at {}, {}'.format(t_stage[0].Start, show_clock(user_config.show_clock)))
        
        power_system.set_initialconditions(t_stage.initialTime, stg, stage_solutions)

        try: 
            stage_solution, instance = create_solve_problem(power_system, t_stage, scenario_tree, multistage=True, stage_number=stg) 
        except OptimizationError:
            #re-do stage, with load shedding allowed
            logging.critical('stage infeasible, re-running with load shedding.')
            power_system.reset_model()
            power_system.set_load_shedding(True)
            try:
                stage_solution, instance = create_solve_problem(power_system, t_stage, scenario_tree, multistage=True, stage_number=stg, rerun=True)
            except OptimizationError:
                if stage_solutions: stage_solutions[-1].saveCSV(joindir(datadir,'last-stage-solved-commitment.csv'), save_final_status=True)
                raise OptimizationError('failed to solve, even with load shedding.')
            power_system.set_load_shedding(False)

        logging.debug('solved... get results... {}'.format(show_clock(user_config.show_clock)))
        
        if stage_solution.is_stochastic:
            # resolve with observed power and fixed status from stochastic solution
            power_system.resolve_stochastic_with_observed(instance, stage_solution)                        
            
            # TODO - evaluate performance against this resolve with perfect information
            
        power_system.get_finalconditions(stage_solution)
        stage_solutions.append(stage_solution)

        if stg < (Nstages-1): # if not the last stage 
            power_system.reset_model()
            #commonscripts.show_memory_growth()
#            if stg==1:
#                commonscripts.show_memory_refs('_VarArray')
#                commonscripts.show_memory_backrefs('_VarArray')
#                commonscripts.show_memory_backrefs('Piecewise')
    return stage_solutions,stage_times


def _setup_logging():
    ''' set up the logging to report on the status'''
    kwds = dict(level = user_config.logging_level, format='%(levelname)s: %(message)s')
    if user_config.logging_filename: kwds['filename']=user_config.logging_filename
    logging.basicConfig(**kwds)


def main():
    '''
    The command line interface for minpower. Described by:
    minpower --help
    '''
    import argparse,os,traceback,sys

    parser = argparse.ArgumentParser(description='Minpower command line interface')
    parser.add_argument('directory', type=str,
                       help='the direcory of the problem you want to solve (or name of minpower demo case)')
    parser.add_argument('--solver','-s',  type=str, 
                    default=user_config.solver,
                    help='the solver name used to solve the problem (e.g. cplex, gurobi, glpk)')
    parser.add_argument('--visualization','-v',action="store_true", 
                    default=user_config.show_visualization,
                    help='save a visualization of the solution')
    parser.add_argument('--breakpoints','-b',  type=int, 
                    default=user_config.num_breakpoints,
                    help='number of breakpoints to use in piece-wise linearization of polynomial costs')
    parser.add_argument('--commitment_hours','-c', type=int, 
                    default=user_config.hours_commitment,
                    help='number hours per commitment in a rolling UC (exclusive of overlap)')
    parser.add_argument('--overlap_hours','-o', type=int, 
                    default=user_config.hours_commitment_overlap,
                    help='number hours to overlap commitments in a rolling UC')
    parser.add_argument('--problemfile','-p',action="store_true", 
                    default=user_config.problem_filename,
                    help='flag to write the problem formulation to a problem-formulation.lp file -- useful for debugging')
    parser.add_argument('--duals_off','-u',action="store_true", 
                    default=not user_config.duals,
                    help='flag to skip getting the the duals, or prices, of the optimization problem')
    parser.add_argument('--dispatch_decommit_allowed','-d', action="store_true", 
                    default=user_config.dispatch_decommit_allowed,
                    help='flag to allow de-commitment of units in an ED -- useful for getting initial conditions for UCs')
    parser.add_argument('--logfile','-l',type=str,
                    default=user_config.logging_filename,
                    help='log file, default is to log to terminal')
    parser.add_argument('--scenarios',type=int, 
                    default=user_config.scenarios_limit,
                    help='limit the number of scenarios to N')
    # parser.add_argument('--solution_file',type=str,default=False,
    #                    help='save solution file to disk')
    parser.add_argument('--profile',action="store_true",
                    default=False,
                    help='run cProfile and output to minpower.profile')
    parser.add_argument('--error','-e',action="store_true",
                    default=False,
                    help='redirect error messages to the standard output (useful for debugging on remote machines)')

    #figure out the command line arguments
    args = parser.parse_args()

    directory=args.directory

    if not os.path.isdir(directory):
        msg='There is no folder named "{}".'.format(directory)
        raise OSError(msg)
    user_config.update(vars(args))
    user_config.duals = not args.duals_off
    
    
    if args.profile:
        print 'run profile'
        import cProfile
        prof = cProfile.Profile()
        prof.runcall(solve_problem, directory)
        prof.dump_stats('minpower.profile')

    else:
        #solve the problem with those arguments
        try: solve_problem(directory)
        except:
            if args.error:
                print 'There was an error:'
                traceback.print_exc(file=sys.stdout)
            else: raise
