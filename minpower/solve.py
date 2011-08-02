"""
Power systems optimization problem solver
(ED, OPF, UC, and SCUC problems).
"""

import sys,os,logging

import optimization
import get_data
import powersystems
import results
import config
from commonscripts import joindir

    
def _setup_logging(fn):
    ''' set up the logging to report on the status'''
    logging.basicConfig( level=logging.INFO, format='%(levelname)s: %(message)s')
    return fn
    
@_setup_logging
def problem(datadir='./tests/uc/',
    outputs=dict(
        shell=True,problemfile=True,
        vizualization=True,csv=True),
    solver=config.optimization_solver):
    
    """ Solve a optimization problem in a directory.
        Problem type is determined from the data.
            
        :param datadir: directory of data files, see :mod:`get_data`
        :param outputs: dictionary of outputs flags: {shell, problemfile, vizualization,csv}
        :param solver:  choice of solver
        
        :returns: :class:`~results.Solution` object
    """
    
    buses,lines,times=get_data.parsedir(datadir)

    if times.spanhrs<=24:
        problemfile=joindir(datadir,'problem-formulation.lp') if outputs['problemfile'] else None
        problem=create_problem(buses,lines,times,problemfile)
        optimization.solve(problem,solver)
        solution=results.makeSolution(times=times,lines=lines,buses=buses,problem=problem,datadir=datadir)
    else: #split into multi-stage problem
        problemsL,stageTimes=create_problem_multistage(buses,lines,times)
        solution=results.makeMultistageSolution(problemsL=problemsL,times=times,stageTimes=stageTimes,buses=buses,lines=lines,datadir=datadir)

    
    if outputs['shell']: solution.show()
    if outputs['csv']: solution.saveCSV()
    if outputs['vizualization']: solution.vizualization()
    return solution

def create_problem(buses,lines,times, filename=None):
    """
        Create a power systems optimization problem.
        
        :param buses: list of :class:`~powersystems.Bus` objects
        :param lines: list of :class:`~powersystems.Line` objects
        :param times: :class:`~schedule.Timelist` object
        :param filename: (optional) create a .lp file of the problem
        
        :returns: :class:`~optimization.Problem` object
    """

    Bmatrix=powersystems.Network(buses,lines).Bmatrix
    prob=optimization.newProblem()
    costs=[]
    
    for bus in buses:
        if len(buses)>1: bus.add_timevars(times)
        
        for gen in bus.generators:
            gen.add_timevars(times)
            prob.addConstraints(gen.constraints(times))
            for time in times: costs.append(gen.cost(time))

        for load in bus.loads:
            load.add_timevars(times)
            prob.addConstraints(load.constraints(times))
            for time in times: costs.append(-1*load.benifit(time))
            
    for line in lines:
        line.add_timevars(times)
        prob.addConstraints(line.constraints(times,buses))
                    
    for bus in buses:
        prob.addConstraints(bus.constraints(times,Bmatrix,buses))
        
    prob.addObjective( optimization.sumVars(costs) )
    
    if filename is not None: prob.write(filename)
    return prob





def create_problem_multistage(buses,lines,times,intervalHrs=1.0,stageHrs=24):
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
    import time as systemtime
    stageTimes=times.subdivide(hrsperdivision=stageHrs,hrsinterval=intervalHrs)
    problemsL=[]
    
    def set_initialconditions(buses,initTime):
        for bus in buses:
            for gen in bus.generators:
                try: 
                    gen.setInitialCondition(time=initTime,**gen.finalstatus)
                    del gen.finalstatus
                except AttributeError: pass #first stage of problem already has initial time definied

    def get_finalconditions(buses,times):
        for bus in buses:
            for gen in bus.generators: gen.finalstatus=gen.getstatus(t=times[-1],times=times)

    for t_stage in stageTimes:
        logging.info('Stage from {s} to {e}'.format(s=t_stage[0].Start, e=t_stage[-1].End))
        timeit0= systemtime.time()
        set_initialconditions(buses,t_stage.initialTime)
        stageproblem=create_problem(buses,lines,t_stage)
        logging.info('setup in {t:0.1f}s'.format(t=systemtime.time()-timeit0))
        optimization.solve(stageproblem)
        logging.info('solved in {t:0.1f}s'.format(t=systemtime.time()-timeit0))
        if stageproblem.status==1:
            problemsL.append(stageproblem)
            finalcondition=get_finalconditions(buses,t_stage)
        else: 
            stageproblem.write('infeasible-problem.lp')
            raise optimization.OptimizationError('Infeasible problem - writing to .lp file for examination.')
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
