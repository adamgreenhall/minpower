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
    
    _setup_logging(logging_level)
    
    generators,loads,lines,times=get_data.parsedir(datadir)
    power_system=powersystems.PowerSystem(generators,loads,lines,                 
                num_breakpoints=num_breakpoints,
                load_shedding_allowed=False,
                spinning_reserve_requirement=0,
                dispatch_decommit_allowed=False,)
    
    if times.spanhrs<=hours_commitment:
        problem=create_problem(power_system,times)
        optimization.solve(problem,solver,problem_filename=joindir(datadir,'problem-formulation.lp'))
        if problem.solved:
            solution=results.make_solution(power_system,times,problem=problem,datadir=datadir)
        else: 
            raise optimization.OptimizationError('problem not solved')
    else: #split into multiple stages and solve
        stage_solutions,stage_times=solve_multistage(power_system,times,datadir,
                                                       stage_hours=hours_commitment,
                                                       overlap_hours=hours_commitment_overlap,
                                                       )
        solution=results.make_multistage_solution(power_system,stage_times,datadir,stage_solutions)
        logging.info('problem solved in {}'.format(solution.solve_time))
        
    if shell: solution.show()
    if csv: solution.saveCSV()
    if vizualization: solution.vizualization()
    return solution

def create_problem(power_system,times):
    """
        Create a power systems optimization problem.
        
        :param power_system: a :class:`~powersystems.PowerSystem` object
        :param times: :class:`~schedule.Timelist` object
        
        :returns: :class:`~optimization.Problem` object
    """
    
    prob=optimization.newProblem()
    variables =power_system.create_variables(times)
    objective=power_system.create_objective(times)
    constraints=power_system.create_constraints(times)
    
    for nm,v in variables.items(): prob.add_variable(v)
    prob.add_objective(objective)
    for nm,c in constraints.items(): 
        try: prob.add_constraint(c)
        except TypeError:
            print 'error in adding constraint',nm
            print 'expression is: ',c
            raise
    return prob






def solve_multistage(power_system,times,datadir,
                              interval_hours=None,
                              stage_hours=config.default_hours_commitment,
                              overlap_hours=config.default_hours_commitment_overlap,
                              writeproblem=False,
                              showclock=True):
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

    def get_finalconditions(power_system,times,lastproblem):
        t_back=overlap_hours/times.intervalhrs
        next_stage_first_time = times[-1-int(t_back)]         
        for bus in power_system.buses:
            for gen in bus.generators:
                gen.update_variables()
                gen.finalstatus=gen.getstatus(t=next_stage_first_time,times=times)


    for t_stage in stage_times:
        logging.info('Stage starting at {}, {}'.format(t_stage[0].Start, 'clock time={}'.format(wallclocktime.now().strftime('%H:%M:%S')) if showclock else ''))
        
        set_initialconditions(buses,t_stage.initialTime)
        stage_problem=create_problem(power_system,t_stage)
        if writeproblem: stage_problem.write(joindir(datadir,'problem-stage{}.lp'.format(t_stage[0].Start.strftime('%Y-%m-%d--%H-%M'))))
        optimization.solve(stage_problem)
        
        if not stage_problem.solved: 
            #re-do stage, with load shedding allowed
            logging.critical('Stage infeasible, re-running with load shedding.')
            power_system.set_load_shedding(True)
            stage_problem=create_problem(power_system,t_stage)
            optimization.solve(stage_problem)
            power_system.set_load_shedding(False)
            
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

  
def _setup_logging(level):
    ''' set up the logging to report on the status'''
    logging.basicConfig( level=level, format='%(levelname)s: %(message)s')
