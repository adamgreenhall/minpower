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
import time as timer

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
    start_time = timer.time()
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
<<<<<<< HEAD
        problem=create_problem(power_system,times)
        if problemfile: problemfile=joindir(datadir,'problem-formulation.lp')
        problem.solve(solver,problem_filename=problemfile,get_duals=get_duals)
        
        if problem.solved:
            solution=results.make_solution(power_system,times,problem=problem,datadir=datadir)
        else: 
            raise optimization.OptimizationError('problem not solved')
<<<<<<< HEAD
    else: #split into multi-stage problem
<<<<<<< HEAD
<<<<<<< HEAD
        problemsL,stageTimes=create_problem_multistage(buses,lines,times,datadir,num_breakpoints=num_breakpoints)
        solution=results.makeMultistageSolution(problemsL=problemsL,times=times,stageTimes=stageTimes,buses=buses,lines=lines,datadir=datadir)
<<<<<<< HEAD

<<<<<<< HEAD
    logging.info('displaying solution')
    if outputs['shell']: solution.show()
    if outputs['csv']: solution.saveCSV()
    if outputs['vizualization']: solution.vizualization()
=======
=======
=======
        problemsL,stageTimes=create_problem_multistage(buses,lines,times,datadir,
=======
        problemsL,stageTimes=create_problem_multistage(power_system,times,datadir,
>>>>>>> refactor solve()
                                                       stageHrs=hours_commitment,
                                                       overlap_hours=hours_commitment_overlap,
                                                       num_breakpoints=num_breakpoints,
                                                       )
<<<<<<< HEAD
<<<<<<< HEAD
        solution=results.makeMultistageSolution(problemsL=problemsL,
            buses=buses,lines=lines,
<<<<<<< HEAD
            times=times,stageTimes=stageTimes,
            datadir=datadir)
>>>>>>> added rolling UC overlap options. tested schedule.Timelist.subdivide function, but need to test integration
=======
            times=times,stageTimes=stageTimes,overlap_hours=hours_commitment_overlap,
            datadir=datadir
            )
>>>>>>> fixed results with overlap, by adding non_overlap_times to each stage time
=======
        solution=results.makeMultistageSolution(power_system,times,datadir,
                                                problemsL,stageTimes,
                                                overlap_hours=hours_commitment_overlap,
                                                )
>>>>>>> refactor solve()
        logging.info('problem solved in {}'.format(solution.solveTime))
<<<<<<< HEAD
>>>>>>> cleaner handling of different bid models. fix for the convex bid model, due to confusion from ugly code.
    
    generators=buses[0].generators
    for t in times:
        print t,[g.startup[t] for g in generators],[g.shutdown[t] for g in generators]
    
=======
=======
        solution=results.make_multistage_solution(power_system,times,datadir,
                                                problemsL,stageTimes,
                                                overlap_hours=hours_commitment_overlap,
                                                )
=======
=======
        solution=create_solve_problem(power_system,times,datadir,solver,problemfile,get_duals)
>>>>>>> testing memory differences (pulled some code for create_solve_problem from DR_update)
    else: #split into multiple stages and solve
        stage_solutions,stage_times=solve_multistage(power_system,times,datadir,
                                                       solver=solver,
                                                       get_duals=get_duals,
                                                       stage_hours=hours_commitment,
                                                       overlap_hours=hours_commitment_overlap,
                                                       problemfile=problemfile,
                                                       )
        solution=results.make_multistage_solution(power_system,stage_times,datadir,stage_solutions)
<<<<<<< HEAD
<<<<<<< HEAD
>>>>>>> rework of multistage results - testing
        logging.info('problem solved in {}'.format(solution.solve_time))
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
=======
        logging.info('problem solved in {} ... finished at {}'.format(solution.solve_time,show_clock()))
<<<<<<< HEAD
>>>>>>> fix for fuelcost default with different types of NG
        
>>>>>>> fix for linear cost curves - now: cost=a*u+b*P
=======
    
<<<<<<< HEAD
    tracker.create_snapshot('solutions solved')
=======
>>>>>>> clean up problem time reporting
    
>>>>>>> setting up pympler test
=======
>>>>>>> added yaml to setup.py reqs. cleanup
    if shell: solution.show()
    if csv: solution.saveCSV()
<<<<<<< HEAD
    if vizualization: solution.vizualization()
>>>>>>> option handling now flat input instead of dict
=======
    if visualization: solution.visualization()
<<<<<<< HEAD
>>>>>>> changed problem file to false by default. renamed visualization.
=======
    if solution_file: solution.save(solution_file)
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    HtmlStats(tracker=tracker).create_html('profile.html')
    show_backref_chain('_VarElement')
    show_backrefs('_VarElement')
>>>>>>> testing memory differences (pulled some code for create_solve_problem from DR_update)
=======
    if profile_memory:
        HtmlStats(tracker=tracker).create_html('profile.html')
        #show_backref_chain('_VarElement')
        #show_backrefs('_VarElement')
>>>>>>> memory and processor profiling
=======
>>>>>>> added yaml to setup.py reqs. cleanup
=======
    logging.info('total time: {}s'.format(timer.time()-start_time))
>>>>>>> clean up problem time reporting
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
<<<<<<< HEAD

    Bmatrix=powersystems.Network(buses,lines).Bmatrix
    prob=optimization.newProblem()
    costs=[]
    
    for bus in buses:
        if len(buses)>1: bus.add_timevars(times)
        
        for gen in bus.generators:
<<<<<<< HEAD
<<<<<<< HEAD
            gen.add_timevars(times)
=======
            problemvars.extend(gen.add_timevars(times,dispatch_decommit_allowed))
>>>>>>> initial generator status defaults to off if not specified. solve directory defaults to current directory if not specified. initial conditions spec now accepts ED results.
=======
            problemvars.extend(gen.add_timevars(times,num_breakpoints,dispatch_decommit_allowed))
>>>>>>> added user breakpoint control by moving buildCostModel into add_timevars
            prob.addConstraints(gen.constraints(times))
            for time in times: costs.append(gen.cost(time))

        for load in bus.loads:
            problemvars.extend(load.add_timevars(times,load_shedding_allowed))
            prob.addConstraints(load.constraints(times))
            for time in times: costs.append(-1*load.benifit(time))
            
    for line in lines:
        line.add_timevars(times)
        prob.addConstraints(line.constraints(times,buses))
                    
    for bus in buses:
<<<<<<< HEAD
        problemvars.extend(bus.add_timevars(times))
        prob.addConstraints(bus.constraints(times,Bmatrix,buses))
        
=======
        problemvars.extend([v for k,v in bus.add_timevars(times).iteritems()])
        prob.addConstraints(bus.create_constraints(times,Bmatrix,buses))
    
    
    for v in problemvars: prob.addVar(v)
<<<<<<< HEAD
>>>>>>> this is going to be a major refactor. putting on hold for now.
    prob.addObjective( optimization.sumVars(costs) )
=======
    prob.addObjective( optimization.sum_vars(costs) )
>>>>>>> refactored powersystems. moving on to bidding
    
<<<<<<< HEAD
=======
#   if filename is not None: prob.write(filename)
>>>>>>> debugging solution constraint problem
=======
    
    
    
    logging.debug('initialized problem {}'.format(show_clock()))
    power_system.create_variables(times)
    logging.debug('created variables {}'.format(show_clock()))
    power_system.create_objective(times)
    logging.debug('created objective {}'.format(show_clock()))
<<<<<<< HEAD
    constraints=power_system.create_constraints(times)
<<<<<<< HEAD
<<<<<<< HEAD
    total_cost =power_system.objective
<<<<<<< HEAD
    for nm,v in variables.items(): prob.addVar(v)
    for nm,c in constraints.items(): prob.addConstraint(c)
    prob.addObjective(total_cost)
>>>>>>> refactor solve()
=======
=======
=======
    logging.debug('created constraints {}'.format(show_clock()))
<<<<<<< HEAD
>>>>>>> debugging times for problem creation
    
<<<<<<< HEAD
>>>>>>> added create_objective method across opt obj classes. need to test.
    for nm,v in variables.items(): prob.add_variable(v)
    prob.add_objective(objective)
    for nm,c in constraints.items(): 
        try: prob.add_constraint(c)
        except TypeError:
            print 'error in adding constraint',nm
            print 'expression is: ',c
            raise
<<<<<<< HEAD
    prob.add_objective(total_cost)
>>>>>>> first working pass through solver (results still needs major rework
=======
>>>>>>> added create_objective method across opt obj classes. need to test.
    return prob





<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
def create_problem_multistage(buses,lines,times,datadir,intervalHrs=None,stageHrs=24,writeproblem=False):
=======
def create_problem_multistage(buses,lines,times,datadir,intervalHrs=1,stageHrs=24,writeproblem=False):
>>>>>>> prep. for merge. added coin solver to optimization. added write problem option to solve.
=======
def create_problem_multistage(buses,lines,times,datadir,intervalHrs=None,stageHrs=24,writeproblem=False, showclock=True):
>>>>>>> moved savestage() meth. to results. added wallclock timer display for multistage problems. added write_last_stage_status call for debugging multistage fails.
=======

=======
=======
>>>>>>> added create_solve_problem
    for v in variables.values(): prob.add_variable(v)
    for c in constraints.values(): prob.add_constraint(c)
    prob.add_objective(objective)
    return prob
=======
    power_system.create_constraints(times)
    logging.debug('created constraints {}'.format(show_clock()))
    return

<<<<<<< HEAD
#def make_opt_problem(variables,constraints,objective):
#    prob=Problem()
#    for v in variables.values(): prob.add_variable(v)
#    for c in constraints.values(): prob.add_constraint(c)
#    prob.add_objective(objective)
#    return prob

>>>>>>> basic conversion of power_system to OptimziationProblem object
=======
>>>>>>> working on making rolling commitments work

>>>>>>> documentation overhaul - up to schedule
def solve_multistage(power_system,times,datadir,
                              solver=config.optimization_solver,
                              interval_hours=None,
                              stage_hours=config.default_hours_commitment,
                              overlap_hours=config.default_hours_commitment_overlap,
                              problemfile=False,
                              get_duals=True,
                              showclock=True):
>>>>>>> fix for multistage with rbeakpoint option
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

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    def get_finalconditions(buses,times):
=======
    def get_finalconditions(buses,times,lastproblem):
        t_back=overlap_hours/times.intervalhrs
        next_stage_first_time = times[-1-int(t_back)]         
>>>>>>> working rolling UC overlap hours
        for bus in buses:
<<<<<<< HEAD
            for gen in bus.generators: gen.finalstatus=gen.getstatus(t=times[-1],times=times)

=======
=======
    def get_finalconditions(power_system,times,lastproblem):
=======
    def get_finalconditions(power_system,times):
>>>>>>> testing memory differences (pulled some code for create_solve_problem from DR_update)
        t_back=overlap_hours/times.intervalhrs
        next_stage_first_time = times[-1-int(t_back)]         
<<<<<<< HEAD
        for bus in power_system.buses:
>>>>>>> rework of multistage results - testing
            for gen in bus.generators:
<<<<<<< HEAD
                gen.update_vars(times, lastproblem)
<<<<<<< HEAD
                gen.finalstatus=gen.getstatus(t=times[-1],times=times)
>>>>>>> update_vars changed to just require problem (variables are embbeded in problem instead of solution)
=======
=======
                gen.update_variables()
>>>>>>> minor changes for multistage
                gen.finalstatus=gen.getstatus(t=next_stage_first_time,times=times)
=======
        for gen in power_system.generators():
            gen.finalstatus=gen.getstatus(t=next_stage_first_time,times=times)
>>>>>>> add evaluate option to costs (coopr sums). add storage of generation power and status for UC results

>>>>>>> working rolling UC overlap hours

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
