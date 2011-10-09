"""
Power systems optimization problem solver
(ED, OPF, UC, and SCUC problems).
"""

import sys,os,logging
from datetime import datetime as wallclocktime

import optimization
import get_data
import powersystems
import results
import config
from commonscripts import joindir,flatten

  
def _setup_logging(fn):
    ''' set up the logging to report on the status'''
    logging.basicConfig( level=config.logging_level, format='%(levelname)s: %(message)s')
    return fn
    
@_setup_logging
def problem(datadir='.',shell=True,problemfile=True,
        vizualization=True,csv=True,solver=config.optimization_solver):
    """ Solve a optimization problem in a directory.
        Problem type is determined from the data.
            
        :param datadir: directory of data files, see :mod:`get_data`
        :param outputs: dictionary of outputs flags: {shell, problemfile, vizualization,csv}
        :param solver:  choice of solver
        
        :returns: :class:`~results.Solution` object
    """
    
    buses,lines,times=get_data.parsedir(datadir)

    if times.spanhrs<=24:
        problem=create_problem(buses,lines,times)
        optimization.solve(problem,solver)
        if problemfile: problem.write(joindir(datadir,'problem-formulation.lp'))
        if problem.solved:
            solution=results.makeSolution(times=times,lines=lines,buses=buses,problem=problem,datadir=datadir)
        else: 
            raise optimization.OptimizationError('problem not solved')
    else: #split into multi-stage problem
        problemsL,stageTimes=create_problem_multistage(buses,lines,times,datadir)
        solution=results.makeMultistageSolution(problemsL=problemsL,times=times,stageTimes=stageTimes,buses=buses,lines=lines,datadir=datadir)
        logging.info('problem solved in {}'.format(solution.solveTime))
    
    if shell: solution.show()
    if csv: solution.saveCSV()
    if vizualization: solution.vizualization()
    return solution

def create_problem(buses,lines,times,load_shedding_allowed=False,dispatch_decommit_allowed=False):
    """
        Create a power systems optimization problem.
        
        :param buses: list of :class:`~powersystems.Bus` objects
        :param lines: list of :class:`~powersystems.Line` objects
        :param times: :class:`~schedule.Timelist` object
        
        :returns: :class:`~optimization.Problem` object
    """

    Bmatrix=powersystems.Network(buses,lines).Bmatrix
    prob=optimization.newProblem()
    costs=[]
    problemvars=[]
    
    for bus in buses:
        if len(buses)>1: bus.add_timevars(times)
        
        for gen in bus.generators:
            problemvars.extend(gen.add_timevars(times,dispatch_decommit_allowed))
            prob.addConstraints(gen.constraints(times))
            for time in times: costs.append(gen.cost(time))

        for load in bus.loads:
            problemvars.extend(load.add_timevars(times,load_shedding_allowed))
            prob.addConstraints(load.constraints(times))
            for time in times: costs.append(-1*load.benifit(time))
            
    for line in lines:
        problemvars.extend(line.add_timevars(times))
        prob.addConstraints(line.constraints(times,buses))
                    
    for bus in buses:
        problemvars.extend(bus.add_timevars(times))
        prob.addConstraints(bus.constraints(times,Bmatrix,buses))
    
    for v in problemvars: prob.addVar(v)
    prob.addObjective( optimization.sumVars(costs) )
    
    return prob






def create_problem_multistage(buses,lines,times,datadir,intervalHrs=None,stageHrs=24,writeproblem=False, showclock=True):
    """
    Create a multi-stage power systems optimization problem.
    Each stage will be one optimization run. A stage's final
    conditions will be the next stage's initial condition.
    Multi-stage problems are generally used for UCs over many days.
    
    :param buses: list of :class:`~powersystems.Bus` objects
    :param lines: list of :class:`~powersystems.Line` objects
    :param times: :class:`~schedule.Timelist` object
    :param intervalHrs: define the number of hours per interval
    :param stageHrs: define the number of hours per stage
    
    
    :returns: a list of :class:`~optimization.Problem` objects (one per stage)
    :returns: a list of :class:`~schedule.Timelist` objects (one per stage)
    
    """
        
    if not intervalHrs: intervalHrs=times.intervalhrs
        
    stageTimes=times.subdivide(hrsperdivision=stageHrs,hrsinterval=intervalHrs)
    problemsL=[]

    
    def set_initialconditions(buses,initTime):
        for bus in buses:
            for gen in bus.generators:
                try: 
                    gen.setInitialCondition(time=initTime,**gen.finalstatus)
                    del gen.finalstatus
                except AttributeError: pass #first stage of problem already has initial time definied

    def get_finalconditions(buses,times,lastproblem):
        for bus in buses:
            for gen in bus.generators:
                gen.update_vars(times, lastproblem)
                gen.finalstatus=gen.getstatus(t=times[-1],times=times)


    for t_stage in stageTimes:
        logging.info('Stage starting at {} {}'.format(t_stage[0].Start, 'time={}'.format(wallclocktime.now()) if showclock else ''))
        set_initialconditions(buses,t_stage.initialTime)
        stageproblem=create_problem(buses,lines,t_stage)
        if writeproblem: stageproblem.write(joindir(datadir,'problem-stage{}.lp'.format(t_stage[0].Start.strftime('%Y-%m-%d--%H-%M'))))
        
        optimization.solve(stageproblem)
        if stageproblem.status!=1: 
            #redo stage, with shedding allowed
            logging.warning('Stage infeasible, re-runnning with load shedding.')
            stageproblem=create_problem(buses,lines,t_stage,load_shedding_allowed=True)
            optimization.solve(stageproblem)
            
        if stageproblem.status==1:
            get_finalconditions(buses,t_stage,stageproblem)
            stage_sln=results.get_stage_solution(stageproblem,buses,t_stage)
            problemsL.append(stage_sln)
        else: 
            print stageproblem.status,stageproblem.statusText()
            stageproblem.write('infeasible-problem.lp')
            results.write_last_stage_status(buses,t_stage)
            msg='Infeasible problem - writing to .lp file for examination.'
            raise optimization.OptimizationError(msg)
    return problemsL,stageTimes

if __name__ == "__main__": 
    ''' command line input'''
    _setup_logging()
    if len(sys.argv)==1: problem()
    elif len(sys.argv)==2: 
        datadir=sys.argv[1]
        if not os.path.isdir(datadir):
            raise OSError( "data directory does not exist: '{d}'".format(d=datadir) )
        problem(datadir=datadir)
    else: 
        raise IOError('solve.main() takes only one input argument (the directory). {n} inputs passed'.format(n=len(sys.argv)))
