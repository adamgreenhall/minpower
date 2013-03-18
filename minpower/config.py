"""
Provide the defaults and configuration for other modules.
`user_config` is treated as a global in minpower.
"""
import os
import sys
from ConfigParser import SafeConfigParser
from commonscripts import DotDict, joindir

parser = SafeConfigParser()
parser.read([
    # the minpower default set, from the minpower/configuration directory
    joindir(os.path.split(__file__)[0], 'configuration/minpower.cfg'),
    # the user's global overrides, from the home directory
    os.path.expanduser('~/minpower.cfg'),
    os.path.expanduser('~/.minpowerrc'),
])

option_types = dict(
    duals=bool,
    breakpoints=int,
    hours_commitment=int,
    hours_overlap=int,
    
    cost_load_shedding=float,
    cost_wind_shedding=float,
    economic_wind_shed=bool,
    dispatch_decommit_allowed=bool,
    solver=str,
    mipgap=float,
    solver_time_limit=float,
    
    reserve_fixed=float,
    reserve_load_fraction=float,

    faststart_resolve=bool,

    visualization=bool,
    logging_level=int,
    problem_file=bool,
    output_prefix=bool,
    debugger=bool,

    scenarios=int,
    deterministic_solve=bool,
    perfect_solve=bool,
    scenarios_directory=str,

    standalone=bool,
    pid=str,

    wind_forecast_adder=float,
    wind_multiplier=float,
    wind_capacity_factor=float,
    wind_error_multiplier=float,

    load_multiplier=float,
    load_adder=float,

    pmin_multiplier=float,
    ramp_limit_multiplier=float,

    ignore_minhours_constraints=bool,
    ignore_ramping_constraints=bool,
    ignore_pmin_constraints=bool,

    on_complete_script=str,

    file_gens=str,
    file_loads=str,
    file_lines=str,
    file_init=str,

    # HACKs to help out resetting the config in testing
    directory=str,
    store_filename=str,
)

def parser_value(parser, section, key, opt_type):
    meth = 'get'
    if opt_type==bool:
        meth += 'boolean'
    elif opt_type==str:
        pass
    else:
        meth += str(opt_type).split("'")[1]
    return getattr(parser, meth)(section, key)

def parse_config(parser):
    minpower_config = DotDict(
        dict( [(k, parser_value(parser, 'minpower', k, v)) \
            for k, v in option_types.iteritems()]))
    
    s = 'scheduler'
    scheduler_config = DotDict(dict(
        email=parser.get(s, 'email'),
        hours_limit=parser.getint(s, 'hours_limit'),
        memory=parser.getint(s, 'memory'),
        scheduler_mode=parser.get(s, 'scheduler_mode'),
        verbose=parser.getboolean(s, 'verbose'),
        ))
    
    return minpower_config, scheduler_config

user_config, scheduler_config = parse_config(parser)

available_solvers = []
for solver in parser.options('available_solvers'):
    if parser.getboolean('available_solvers', solver):
        available_solvers.append(solver)

def filter_non_defaults(x, defaults):
    return dict((k, v) for k, v in x.iteritems() if \
        (k not in defaults) or (v != defaults[k])
        )

def get_dir_config(directory):
    '''
    pull the config from a specific directory.
    this allows post-load updating of the user_config.
    '''
    dirparser = SafeConfigParser()
    dirparser.read([
        # the minpower default set, from the minpower/configuration directory
        # need this to set the defaults
        joindir(os.path.split(__file__)[0], 'configuration/minpower.cfg'),
        # need the home directory overrides too
        os.path.expanduser('~/minpower.cfg'),
        os.path.expanduser('~/.minpowerrc'),
        # the directory's defaults
        joindir(directory, 'minpower.cfg'),
    ])
    
    new_user_config, new_scheduler_conifg = parse_config(dirparser)
    # return (filter_non_defaults(new_user_config, user_config),
    #    filter_non_defaults(new_scheduler_conifg, scheduler_config))
    return new_user_config, new_scheduler_conifg
    
def parse_command_line_config(parser, preparsed_args=None):
    # get the directory first
    
    parser = setup_parser_args(parser)
    
    directory = parser.parse_args(preparsed_args).directory
        
    # an extra config parse to make sure that if you are calling a case but not 
    # in the case directory, the case config gets used
    new_user_config, new_scheduler_config = get_dir_config(directory)
    user_config.update(new_user_config)
    scheduler_config.update(new_scheduler_config)
    
    parser.set_defaults(**dict(user_config))

    #figure out the command line arguments
    clargs = vars(parser.parse_args(preparsed_args))

    user_config.update(clargs)

    user_config.update(dict(directory=directory))
    
    if clargs.pop('show_config'):
        from pprint import pprint
        pprint(user_config)
        sys.exit()

    return clargs

def add_opt(parser, name, shortcut=None, help=""):
    kwds = dict(help=help, type=option_types[name], default=user_config[name])
    callers = ['--{n}'.format(n=name)]
    
    if shortcut:
        callers.append(shortcut)
    if kwds['type'] == bool:
        kwds['action'] = 'store_true'
        kwds.pop('type')

    parser.add_argument(*callers, **kwds)
    
def setup_parser_args(parser):
    parser.add_argument('directory', type=str,
        help='the direcory of the problem you want to solve')

    add_opt(parser, 'solver', '-s', 
        help='the solver name (e.g. cplex, gurobi, glpk)')
    add_opt(parser, 'visualization', '-v',
        help='save a visualization of the solution')
        
    add_opt(parser, 'breakpoints', '-b',
        help='number of breakpoints to use in piecewise linearization of polynomial costs')
    add_opt(parser, 'hours_commitment','-c',
        help='number hours per commitment in a rolling UC (exclusive of overlap)')
    add_opt(parser, 'hours_overlap','-o',
        help='number hours to overlap commitments in a rolling UC')


    solver_opt = parser.add_argument_group('Solver options')
    add_opt(solver_opt, 'mipgap',
        help='the MIP gap solution tolerence')
    add_opt(solver_opt, 'solver_time_limit', 
        help='the MIP solver time limit (in seconds)')

        
    reserve = parser.add_argument_group('Reserve',
        'Does the system require reserve? The default is no reserve.')
    add_opt(reserve, 'reserve_fixed',
        help='the static amount of reserve required at all times (in MW)')
    add_opt(reserve, 'reserve_load_fraction',
        help='fraction of the total system load which is required as reserve')

    add_opt(parser, 'duals', '-d',
        help='flag to get the duals, or prices, of the optimization problem')
    add_opt(parser, 'dispatch_decommit_allowed',
        help='flag to allow de-commitment of units in an ED -- useful for getting initial conditions for UCs')
    
    add_opt(parser, 'cost_load_shedding', 
        help='the cost to the system to shed a MWh of load')
    add_opt(parser, 'cost_wind_shedding',
        help='the cost to the system to shed a MWh of wind energy')
    add_opt(parser, 'economic_wind_shed',
        help='is wind allowed to be shed for economic reasons ' + \
        '(default is to allow wind shedding only if infeasible)')
        
    
    stochastic = parser.add_argument_group('Stochastic UC',
        'options to modify the behavior of a stochastic problem')
    add_opt(stochastic, 'scenarios',
        help='limit the number of scenarios to N')        
    add_opt(stochastic, 'faststart_resolve', '-F',
        help="""allow faststart units which are off to be
                started up during resolve with observed wind values""")

    stochastic_mode = stochastic.add_mutually_exclusive_group()
    add_opt(stochastic_mode, 'deterministic_solve', '-D',
        help='solve a stochastic problem deterministically using the forecast_filename paramter')
    add_opt(stochastic_mode, 'perfect_solve', '-P',
        help='solve a stochastic problem with perfect information')
    add_opt(stochastic_mode, 'scenarios_directory', 
        help='override scenarios directory for stochastic problem')
        

    add_opt(parser, 'standalone', '-m', 
        help='Make each multi-day commitment its own subprocess (helps with memory issues).')
    add_opt(parser, 'output_prefix', '-p',
        help='Prefix all results files with the process id (for a record of simulataneous solves)')
    add_opt(parser, 'pid', 
        help='Expicitly specify the standalone storage process id')

    debugging = parser.add_argument_group('Debugging tools')
    add_opt(debugging, 'debugger',
        help='use pdb when an error is raised')
    add_opt(debugging, 'problem_file',
        help='flag to write the problem formulation to a problem.lp file')        
    add_opt(parser, 'logging_level', 
        help='set the level of detail for logging')
    debugging.add_argument('--profile', action="store_true", default=False,
        help='run cProfile and output to minpower.profile')
    debugging.add_argument('--show_config', action='store_true', default=False,
        help='just show the configuration and quit')
    debugging.add_argument('--keep_lp_files', action='store_true', default=False,
        help='keep a record of all of the solver lp files')
    debugging.add_argument('--standalone_restart', 
        action='store_true', default=False, 
        help='restart a multi-stage standalone problem from where it failed')


    ts = parser.add_argument_group('Timeseries modifiers',
        'Alter the timeseries after parsing the data.')
    
    wind_modifier = ts.add_mutually_exclusive_group()
    add_opt(wind_modifier, 'wind_multiplier', 
        help='scale the wind power by this factor')
    add_opt(wind_modifier, 'wind_capacity_factor', 
        help='scale the wind power to match a given energy capacity factor (defined as a toal wind over total load energy for the timeseries)')
    
    add_opt(ts, 'wind_error_multiplier', 
        help='scale the wind power forecast error by this factor')
    add_opt(ts, 'wind_forecast_adder', 
        help='add a fixed amount (e.g. bias) to the wind power forecast')
    add_opt(ts, 'load_multiplier', 
        help='scale the load power by this factor')
    add_opt(ts, 'load_adder', 
        help='add a fixed amount to the load power')
    
    constraints = parser.add_argument_group('Ignore/relax constraints',
        'Ignore or relax sets of constraints to allow for feasible solutions.')
    add_opt(constraints, 'ignore_minhours_constraints', 
        help='drop the min up/down time constraints on the generators')
    add_opt(constraints, 'ignore_ramping_constraints', 
        help='drop the min ramping power constraints on the generators')
    add_opt(constraints, 'ignore_pmin_constraints', 
        help='drop the min power constraints on the generators')
    add_opt(constraints, 'pmin_multiplier', 
        help='scale the generator minimum power limits by this factor')
    add_opt(constraints, 'ramp_limit_multiplier', 
        help='scale the generator ramp power limits by this factor')

    filenames = parser.add_argument_group('Filenames',
        'Change the default filenames to use when loading data.')
    add_opt(filenames, 'file_gens')
    add_opt(filenames, 'file_loads')
    add_opt(filenames, 'file_lines')
    add_opt(filenames, 'file_init')

    add_opt(parser, 'on_complete_script',  
        help='run a script on completion of the minpower script')

    # NOTE - don't let defaults creep into this defenition
    # that makes resetting the defaults during testing very hard 
    
    return parser
