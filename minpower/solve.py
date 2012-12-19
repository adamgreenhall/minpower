"""
Power systems optimization problem solver
for ED, OPF, UC, and SCUC problems. The :mod:`solve`
module contains the top-level commands for creating
problems and solving them.
"""

import sys, os, logging, subprocess
import time as timer
import argparse
import pdb
from optimization import OptimizationError
import get_data, powersystems, stochastic, results
from config import user_config
from commonscripts import joindir, StreamToLogger, set_trace

def _get_store_filename():
    fnm = 'stage-store.hd5'
    if user_config.output_prefix:
        fnm = '{}-{}'.format(user_config._pid, fnm)

    user_config.store_filename = joindir(user_config.directory, fnm)

def solve_multistage_standalone(power_system, times, scenario_tree, data):
    from standalone import store_times, init_store, get_storage, repack_storage
    
    _get_store_filename()

    stage_times = times.subdivide(
        user_config.hours_commitment, user_config.hours_overlap)

    storage = init_store(power_system, stage_times, data)

    for stg,t_stage in enumerate(stage_times):
        logging.info('Stage starting at {}'.format(t_stage.Start.date()))
        # store current stage times
        storage = store_times(t_stage, storage)
        storage.close()
        storage = None
        command = 'standalone_minpower {dir} {stg} {pid}'.format(
                dir=user_config.directory, stg=stg,
                pid='--pid {}'.format(os.getpid()) if user_config.output_prefix else '')
        try: subprocess.check_call(command, shell=True, stdout=sys.stdout)
        except AttributeError:
            # HACk - avoid error when nose hijacks sys.stdout
            subprocess.check_call(command, shell=True)

    repack_storage()
    storage = get_storage()
    return storage, stage_times

def standaloneUC():
    '''the hook for the ``standalone_minpower`` script'''
    from standalone import store_state, load_state

    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=str, help='the problem direcory')
    parser.add_argument('stg', type=int, help='the stage number')
    parser.add_argument('--pid', type=int, default=None,
        help='the process id of the parent')

    args = parser.parse_args()
    stg = args.stg
    user_config.directory = args.directory
    if args.pid:
        user_config.output_prefix = True
        user_config._pid = args.pid

    _get_store_filename()

    _setup_logging()

    # load stage data
    power_system, times, scenario_tree = load_state()

    sln = create_solve_problem(power_system, times, scenario_tree, stage_number=stg)

    store = store_state(power_system, times, sln)
    store.flush()

    return

def solve_problem(datadir='.',
        shell=True,
        problemfile=False,
        csv=True,
        ):
    """
    Solve a optimization problem specified by spreadsheets in a directory.
    Read in data, create and solve the problem, and return solution.
    The problem type is determined by the data.
    All options are set within `user_config`.
    """

    _setup_logging()
    user_config.directory = datadir
    start_time = timer.time()
    logging.debug('Minpower reading {}'.format(datadir))
    generators, loads, lines, times, scenario_tree, data = get_data.parsedir()
    logging.debug('data read')
    power_system = powersystems.PowerSystem(generators,loads,lines)

    logging.debug('power system initialized')
    if times.spanhrs <= user_config.hours_commitment + user_config.hours_overlap:
        solution = create_solve_problem(power_system, times, scenario_tree)
    else: #split into multiple stages and solve
        if user_config.standalone:
            stage_solutions, stage_times = solve_multistage_standalone(
                power_system, times, scenario_tree, data)
        else:
            stage_solutions, stage_times = solve_multistage(
                power_system, times, scenario_tree, data)
        solution = results.make_multistage_solution(
            power_system, stage_times, stage_solutions)

    if shell:
        if user_config.output_prefix:
            stdout = sys.stdout
            sys.stdout = StreamToLogger()
            solution.show()
            sys.stdout = stdout
        solution.show()
    if csv: solution.saveCSV()
    if user_config.visualization: solution.visualization()
    # if solution_file: solution.save(solution_file)
    logging.info('total time: {}s'.format(timer.time()-start_time))
    return solution


def solve_multistage(power_system, times, scenario_tree=None, data=None):
    stage_times = times.subdivide(
        user_config.hours_commitment, user_config.hours_overlap)

    stage_solutions = []

    for stg, t_stage in enumerate(stage_times):
        logging.info('Stage starting at {}'.format(t_stage.Start.date()))
        # solve
        solution = create_solve_problem(
            power_system, t_stage, scenario_tree, stg)
        # add to stage solutions
        stage_solutions.append(solution)
        # reset model
        power_system.reset_model()
        # set inital state for next stage
        if stg < len(stage_times)-1:
            power_system.set_initialconditions(stage_times[stg+1].initialTime)

    return stage_solutions, stage_times


def create_solve_problem(power_system, times, scenario_tree=None,
    stage_number=None, rerun=False):
    '''create and solve an optimization problem.'''

    if user_config.problemfile:
        user_config.problemfile = joindir(
            user_config.directory, 'problem-formulation.lp')

    create_problem(power_system, times, scenario_tree,
        stage_number, rerun)

    try: 
        instance = power_system.solve()
    except OptimizationError:

        #re-do stage, with load shedding allowed
        logging.critical('stage infeasible, re-running with load shedding.')
        power_system.reset_model()
        power_system.set_load_shedding(True)
        create_problem(power_system, times, scenario_tree, stage_number)
        try:
            instance = power_system.solve()
        except OptimizationError:
            raise OptimizationError('failed to solve, even with load shedding.')
        power_system.set_load_shedding(False)

    logging.debug('solved... get results')

    sln = results.make_solution(power_system, times)

    # resolve with observed power and fixed status
    if sln.is_stochastic:
        power_system.resolve_stochastic_with_observed(instance, sln)
    elif user_config.deterministic_solve:
        power_system.resolve_determinisitc_with_observed(sln)

    if sln.load_shed_timeseries.sum() > 0.01:
        logging.debug('shed {}MW in resolve of stage'.format(
            sln.load_shed_timeseries.sum()))


    power_system.get_finalconditions(sln)

    power_system.set_load_shedding(False)
    sln.stage_number = stage_number
    
    return sln

def create_problem(power_system, times, scenario_tree=None,
    stage_number=None, rerun=False):
    """Create an optimization problem."""

    logging.debug('initialized problem')
    power_system.create_variables(times)
    logging.debug('created variables')
    power_system.create_objective(times)
    logging.debug('created objective')
    power_system.create_constraints(times)
    logging.debug('created constraints')

    if scenario_tree is not None and sum(scenario_tree.shape)>0 and not rerun:
        gen = power_system.get_generator_with_scenarios()
        tree = stochastic.construct_simple_scenario_tree(
            gen.scenario_values[times.Start]['probability'].values.tolist(),
            time_stage=stage_number)

        logging.debug('constructed tree for stage %i'%stage_number)

        stochastic.define_stage_variables(tree, power_system, times)
        power_system = stochastic.create_problem_with_scenarios(
            power_system, times, tree,
            user_config.hours_commitment,
            user_config.hours_overlap,
            stage_number=stage_number)
    return

def _setup_logging():
    ''' set up the logging to report on the status'''
    kwds = dict(
        level=user_config.logging_level,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s %(levelname)s: %(message)s')
    if user_config.logging_filename:
        kwds['filename'] = user_config.logging_filename
    if user_config.output_prefix:
        kwds['filename'] = joindir(user_config.directory,
            '{}.pylog'.format(user_config._pid))
    if (user_config.logging_level > 10) and (not 'filename' in kwds):
        # don't log the time if debugging isn't turned on
        kwds['format'] = '%(levelname)s: %(message)s'
    logging.basicConfig(**kwds)


def main():
    '''
    The command line interface for minpower. For more info use:
    ``minpower --help``
    '''
    import os,traceback,sys

    parser = argparse.ArgumentParser(description='Minpower command line interface')
    parser.add_argument('directory', type=str,
        help='the direcory of the problem you want to solve')
    parser.add_argument('--solver','-s',  type=str,
        default=user_config.solver,
        help='the solver name (e.g. cplex, gurobi, glpk)')
    parser.add_argument('--visualization','-v',action="store_true",
        default=user_config.show_visualization,
        help='save a visualization of the solution')
    parser.add_argument('--breakpoints','-b',  type=int,
        default=user_config.breakpoints,
        help='number of breakpoints to use in piecewise linearization of polynomial costs')
    parser.add_argument('--hours_commitment','-c', type=int,
        default=user_config.hours_commitment,
        help='number hours per commitment in a rolling UC (exclusive of overlap)')
    parser.add_argument('--hours_overlap','-o', type=int,
        default=user_config.hours_overlap,
        help='number hours to overlap commitments in a rolling UC')

    parser.add_argument('--reserve_fixed', type=float,
        default=user_config.reserve_fixed,
        help='The static amount of reserve required at all times (in MW)')
    parser.add_argument('--reserve_load_fraction', type=float,
        default=user_config.reserve_load_fraction,
        help='fraction of the total system load which is required as reserve')

    parser.add_argument('--problemfile',action="store_true",
        default=user_config.problem_filename,
        help='flag to write the problem formulation to a problem-formulation.lp file -- useful for debugging')
    parser.add_argument('--duals','-d',action="store_true",
        default=user_config.duals,
        help='flag to get the duals, or prices, of the optimization problem')
    parser.add_argument('--dispatch_decommit_allowed', action="store_true",
        default=user_config.dispatch_decommit_allowed,
        help='flag to allow de-commitment of units in an ED -- useful for getting initial conditions for UCs')
    parser.add_argument('--logfile','-l',type=str,
        default=user_config.logging_filename,
        help='log file, default is to log to terminal')
    parser.add_argument('--scenarios',type=int,
        default=user_config.scenarios,
        help='limit the number of scenarios to N')

    parser.add_argument('--deterministic_solve', action='store_true',
        default=user_config.deterministic_solve,
        help='solve a stochastic problem deterministically using the forecast_filename paramter')
    parser.add_argument('--perfect_solve', action='store_true',
        default=user_config.perfect_solve,  #False
        help='solve a stochastic problem with perfect information')
    parser.add_argument('--scenarios_directory', type=str,
        default=user_config.scenarios_directory,
        help='override scenarios directory for stochastic problem')
    parser.add_argument('--faststart_resolve', action='store_true',
        default=False,
        help="""allow faststart units which are off to be
                started up during resolve""")

    parser.add_argument('--standalone', '-m', action="store_true", default=False,
        help='Make each multi-day commitment its own subprocess (helps with memory issues).')
    parser.add_argument('--output_prefix','-p', action="store_true",
        default=user_config.output_prefix,
        help = 'Prefix all results files with the process id (for a record of simulataneous solves)')

    parser.add_argument('--profile',action="store_true",
        default=False,
        help='run cProfile and output to minpower.profile')
    parser.add_argument('--error','-e',action="store_true",
        default=False,
        help='redirect error messages to the standard output (useful for debugging on remote machines)')
    parser.add_argument('--debugger',action="store_true",
        default=False,
        help='use pudb when an error is raised')

    #figure out the command line arguments
    args = parser.parse_args()

    directory=args.directory

    if not os.path.isdir(directory):
        msg='There is no folder named "{}".'.format(directory)
        raise OSError(msg)

    user_config.update(vars(args))
    if user_config.output_prefix: user_config._pid = os.getpid()

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
            if args.debugger:
                __, __, tb = sys.exc_info()
                traceback.print_exc()
                pdb.post_mortem(tb)
            else: raise

# for use in dev
if __name__=='__main__': main()
