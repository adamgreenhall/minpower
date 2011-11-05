"""
Power systems optimization problem solver
(ED, OPF, UC, and SCUC problems).
"""

import logging
from datetime import datetime as wallclocktime

import optimization
import get_data
import powersystems
import results
import config
from commonscripts import joindir
    
def problem(datadir='.',
        shell=True,
        problemfile=True,
        vizualization=True,
        csv=True,
        solver=config.optimization_solver,
        num_breakpoints=config.default_num_breakpoints,
        hours_commitment=config.default_hours_commitment,
        hours_commitment_overlap=config.default_hours_commitment_overlap,
        logging_level=config.logging_level,
        ):
    """ Solve a optimization problem in a directory.
        Problem type is determined from the data.
            
        :param datadir: directory of data files, see :mod:`get_data`
        :param outputs: dictionary of outputs flags: {shell, problemfile, vizualization,csv}
        :param solver:  choice of solver
        
        :returns: :class:`~results.Solution` object
    """
    
    setup_logging(logging_level)
    
    generators,loads,lines,times=get_data.parsedir(datadir)
    power_system=powersystems.PowerSystem(generators,loads,lines,                 
                num_breakpoints=num_breakpoints,
                load_shedding_allowed=False,
                spinning_reserve_requirement=0,
                dispatch_decommit_allowed=False,)
    
    if times.spanhrs<=hours_commitment:
        problem=create_problem(power_system,times,num_breakpoints)
        optimization.solve(problem,solver,problem_filename=joindir(datadir,'problem-formulation.lp'))
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
    else: #split into multiple stages and solve
        stage_solutions,stage_times=solve_multistage(power_system,times,datadir,
                                                       stage_hours=hours_commitment,
                                                       overlap_hours=hours_commitment_overlap,
                                                       num_breakpoints=num_breakpoints,
                                                       )
        solution=results.make_multistage_solution(power_system,stage_times,datadir,stage_solutions)
>>>>>>> rework of multistage results - testing
        logging.info('problem solved in {}'.format(solution.solve_time))
>>>>>>> major cleanup of results.py. still need to tackle the multistage commitments
        
>>>>>>> fix for linear cost curves - now: cost=a*u+b*P
    if shell: solution.show()
    if csv: solution.saveCSV()
    if vizualization: solution.vizualization()
>>>>>>> option handling now flat input instead of dict
    return solution

def create_problem(power_system,times,
                   num_breakpoints=config.default_num_breakpoints,
                   load_shedding_allowed=False,
                   dispatch_decommit_allowed=False):
    """
        Create a power systems optimization problem.
        
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
    
    prob=optimization.newProblem()
    variables =power_system.create_variables(times)
    objective=power_system.create_objective(times)
    constraints=power_system.create_constraints(times)
<<<<<<< HEAD
    total_cost =power_system.objective
<<<<<<< HEAD
    for nm,v in variables.items(): prob.addVar(v)
    for nm,c in constraints.items(): prob.addConstraint(c)
    prob.addObjective(total_cost)
>>>>>>> refactor solve()
=======
=======
    
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

def solve_multistage(power_system,times,datadir,
                              interval_hours=None,
                              stage_hours=config.default_hours_commitment,
                              overlap_hours=config.default_hours_commitment_overlap,
                              num_breakpoints=config.default_num_breakpoints,
                              writeproblem=False,
                              showclock=True):
>>>>>>> fix for multistage with rbeakpoint option
    """
    Create a multi-stage power systems optimization problem.
    Each stage will be one optimization run. A stage's final
    conditions will be the next stage's initial condition.
    Multi-stage problems are generally used for UCs over many days.
    
    :param buses: list of :class:`~powersystems.Bus` objects
    :param lines: list of :class:`~powersystems.Line` objects
    :param times: :class:`~schedule.Timelist` object
    :param interval_hours: define the number of hours per interval
    :param stage_hours: define the number of hours per stage (excluding overlap)
    :param overlap_hours: number of hours that stages overlap
    
    :returns: a list of :class:`~optimization.Problem` objects (one per stage)
    :returns: a list of :class:`~schedule.Timelist` objects (one per stage)
    
    """
        
    if not interval_hours: interval_hours=times.intervalhrs
        
    stage_times=times.subdivide(hrsperdivision=stage_hours,hrsinterval=interval_hours,overlap_hrs=overlap_hours)
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
        t_back=overlap_hours/times.intervalhrs
        next_stage_first_time = times[-1-int(t_back)]         
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

>>>>>>> working rolling UC overlap hours

    for t_stage in stage_times:
        logging.info('Stage starting at {}, {}'.format(t_stage[0].Start, 'clock time={}'.format(wallclocktime.now().strftime('%H:%M:%S')) if showclock else ''))
        
        set_initialconditions(buses,t_stage.initialTime)
        stage_problem=create_problem(power_system,t_stage,num_breakpoints=num_breakpoints)
        if writeproblem: stage_problem.write(joindir(datadir,'problem-stage{}.lp'.format(t_stage[0].Start.strftime('%Y-%m-%d--%H-%M'))))
        optimization.solve(stage_problem)
        
        if not stage_problem.solved: 
            #re-do stage, with load shedding allowed
            logging.critical('Stage infeasible, re-running with load shedding.')
            stage_problem=create_problem(power_system,t_stage,num_breakpoints=num_breakpoints,load_shedding_allowed=True)
            optimization.solve(stage_problem)
            
        if stage_problem.solved:
            get_finalconditions(power_system,t_stage,stage_problem)
            #stage_sln=results.get_stage_solution(stage_problem,power_system,t_stage,overlap_hours)
            stage_sln=results.make_solution(power_system,t_stage.non_overlap_times,problem=stage_problem)
            stage_solutions.append(stage_sln)
        else: 
            #print stage_problem.status,stage_problem.statusText()
            stage_problem.write('infeasible-problem.lp')
            results.write_last_stage_status(buses,t_stage)
            msg='Infeasible problem - writing to .lp file for examination.'
            raise optimization.OptimizationError(msg)
    return stage_solutions,stage_times

  
def setup_logging(level):
    ''' set up the logging to report on the status'''
    logging.basicConfig( level=level, format='%(levelname)s: %(message)s')
