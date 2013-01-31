"""
Provide the defaults and configuration for other modules.
`user_config` is treated as a global in minpower.
"""
import os
import sys
import argparse
from ConfigParser import SafeConfigParser
from commonscripts import DotDict, joindir, set_trace

generator_kinds = [
    'generic',
    'coal', 'nuclear',
    'ngst', 'ngcc',
    'nggt',
    'wind',
    'chp'
]

generator_defaults = dict(
    Pmin=dict(generic=0, wind=0),

    costcurvestring=dict(
        generic='3000+25P+.005P^2',
        coal='3011+20.14P+.0084P^2',
        nuclear='5178+12.85P+.0014P^2',
        steamturbine='4793+42.75P+.0024P^2',
        combustionturbine='9586+42.75P+.0012P^2',
        wind='0'
    ),
    is_controllable=dict(generic=True, wind=False),
    power=dict(generic=None),

    Pmax=dict(
        generic=500,
        coal=550,
        nuclear=1117,
        nggt=90,
        ngcc=420,
        ngst=550,  # assume equal to coal fired steam
        wind=100,
    ),

    minuptime=dict(
        generic=0,
        coal=24,
        nuclear=120,
        nggt=0,
        ngcc=6,
        ngst=24,  # assume equal to coal fired steam
        wind=0,
    ),

    mindowntime=dict(
        generic=0,
        coal=2,
        nuclear=18,
        nggt=0,
        ngcc=12,
        ngst=12,  # assume equal to coal fired steam
        wind=0,
    ),

    fuelcost=dict(
        generic=1,
        coal=2.0,  # from EIA national average coal price: http://www.eia.gov/electricity/monthly/
        ngst=4.0,  # midrange forecast from NWPP plan: http://www.nwcouncil.org/energy/powerplan/6/
        ngcc=4.0,
        nggt=4.0,
        nuclear=0.65,  # from NWPP plan - Table I-34: Forecast nuclear fuel prices (2006$/MMBtu)
        wind=0,
    ),


    startupcost=dict(
        generic=0,  # if kind not specified, no startup cost
# from Henry Louie thesis
#        coal=            107800,
#        nuclear=         283500,
#        ngst=             73500,
#        nggt=             36750,
#        wind=                 0,
#        ngcc=             73500, #assume same as NG ST
# from WECC Planning Study, via B.Palmintier -
# http://www.eia.gov/oiaf/beck_plantcosts/
        coal=3581,
        nuclear=100000,
        ngst=3581,
        nggt=7811,
        ngcc=9250,
        wind=0,
    )
)


parser = SafeConfigParser()
parser.read([
    # the minpower default set, from the minpower/configuration directory
    joindir(os.path.split(__file__)[0], 'configuration/minpower.cfg'),
    # the user's global overrides, from the home directory
    os.path.expanduser('~/minpower.cfg'),
    os.path.expanduser('~/.minpowerrc'),
])

def parse_config(parser):
    m = 'minpower'
    return DotDict(dict(
        duals=parser.getboolean(m, 'duals'),
        breakpoints=parser.getint(m, 'breakpoints'),
        hours_commitment=parser.getint(m, 'hours_commitment'),
        hours_overlap=parser.getint(m, 'hours_overlap'),

        cost_load_shedding=parser.getfloat(m, 'cost_load_shedding'),
        cost_wind_shedding=parser.getfloat(m, 'cost_wind_shedding'),
        dispatch_decommit_allowed=
        parser.getboolean(m, 'dispatch_decommit_allowed'),
        solver=parser.get(m, 'solver'),
        mipgap=parser.getfloat(m, 'mipgap'),

        reserve_fixed=parser.getfloat(m, 'reserve_fixed'),
        reserve_load_fraction=parser.getfloat(m, 'reserve_load_fraction'),

        faststart_resolve=parser.getboolean(m, 'faststart_resolve'),

        visualization=parser.getboolean(m, 'visualization'),
        logging_level=parser.getint(m, 'logging_level'),
        problem_file=parser.getboolean(m, 'problem_file'),
        output_prefix=parser.getboolean(m, 'output_prefix'),
        debugger=parser.getboolean(m, 'debugger'),


        scenarios=parser.getint(m, 'scenarios'),
        deterministic_solve=parser.getboolean(m, 'deterministic_solve'),
        perfect_solve=parser.getboolean(m, 'perfect_solve'),
        scenarios_directory=parser.get(m, 'scenarios_directory'),

        standalone=parser.getboolean(m, 'standalone'),

        wind_forecast_adder=parser.getfloat(m, 'wind_forecast_adder'),
        wind_multiplier=parser.getfloat(m, 'wind_multiplier'),
        wind_capacity_factor=parser.getfloat(m, 'wind_capacity_factor'),
        wind_error_multiplier=parser.getfloat(m, 'wind_error_multiplier'),

        load_multiplier=parser.getfloat(m, 'load_multiplier'),
        load_adder=parser.getfloat(m, 'load_adder'),

        pmin_multiplier=parser.getfloat(m, 'pmin_multiplier'),
        ramp_limit_multiplier=parser.getfloat(m, 'ramp_limit_multiplier'),

        ignore_minhours_constraints=parser.getboolean(
            m, 'ignore_minhours_constraints'),
        ignore_ramping_constraints=parser.getboolean(
            m, 'ignore_ramping_constraints'),
        ignore_pmin_constraints=parser.getboolean(
            m, 'ignore_pmin_constraints'),

        on_complete_script=parser.get(m, 'on_complete_script'),

        # HACKs to help out resetting the config in testing
        directory=parser.get(m, 'directory'),
        store_filename=parser.get(m, 'store_filename'),
    ))

user_config = parse_config(parser)

available_solvers = []
for solver in parser.options('available_solvers'):
    if parser.getboolean('available_solvers', solver):
        available_solvers.append(solver)
        


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
        # the directory's defaults    
        joindir(directory, 'minpower.cfg'),
    ])
    
    return parse_config(dirparser)
    
def parse_command_line_config(mainparser):
    # get the directory first
    mainparser.add_argument('directory', type=str,
        help='the direcory of the problem you want to solve')
        
    dirns, other_args = mainparser.parse_known_args()
    directory = dirns.directory
    
    # an extra config parse to make sure that if you are calling a case but not 
    # in the case directory, the case config gets used    
    user_config.update(get_dir_config(directory))

    #figure out the command line arguments
    clargs = vars(create_parser().parse_args(other_args))
        
    user_config.update(clargs)

    if clargs.pop('show_config'):
        from pprint import pprint
        pprint(user_config)
        sys.exit()

    return clargs
    
def create_parser():
    parser = argparse.ArgumentParser(
        description='Minpower command line interface')
        
    parser.add_argument('--solver','-s',  type=str,
        default=user_config.solver,
        help='the solver name (e.g. cplex, gurobi, glpk)')
    parser.add_argument('--visualization','-v',action="store_true",
        default=user_config.visualization,
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

    parser.add_argument('--mipgap',  type=float,
        default=user_config.mipgap,
        help='the MIP gap solution tolerence')

    reserve = parser.add_argument_group('Reserve',
        'Does the system require reserve? The default is no reserve.')
    reserve.add_argument('--reserve_fixed', type=float,
        default=user_config.reserve_fixed,
        help='the static amount of reserve required at all times (in MW)')
    reserve.add_argument('--reserve_load_fraction', type=float,
        default=user_config.reserve_load_fraction,
        help='fraction of the total system load which is required as reserve')

    parser.add_argument('--duals','-d',action="store_true",
        default=user_config.duals,
        help='flag to get the duals, or prices, of the optimization problem')
    parser.add_argument('--dispatch_decommit_allowed', action="store_true",
        default=user_config.dispatch_decommit_allowed,
        help='flag to allow de-commitment of units in an ED -- useful for getting initial conditions for UCs')
    
    parser.add_argument('--cost_wind_shedding', type=float,
        default=user_config.cost_wind_shedding,
        help='the cost to the system to shed a MWh of wind energy')
    parser.add_argument('--cost_load_shedding', type=float,
        default=user_config.cost_load_shedding,
        help='the cost to the system to shed a MWh of load')
        
    
    stochastic = parser.add_argument_group('Stochastic UC',
        'options to modify the behavior of a stochastic problem')
    stochastic.add_argument('--scenarios',type=int,
        default=user_config.scenarios,
        help='limit the number of scenarios to N')        
    stochastic.add_argument('--faststart_resolve', '-F',
        action='store_true', default=user_config.faststart_resolve,
        help="""allow faststart units which are off to be
                started up during resolve with observed wind values""")

    stochastic_mode = stochastic.add_mutually_exclusive_group()
    stochastic_mode.add_argument('--deterministic_solve', '-D',
        action='store_true', default=user_config.deterministic_solve,
        help='solve a stochastic problem deterministically using the forecast_filename paramter')
    stochastic_mode.add_argument('--perfect_solve', '-P', action='store_true',
        default=user_config.perfect_solve,  #False
        help='solve a stochastic problem with perfect information')
    stochastic_mode.add_argument('--scenarios_directory', type=str,
        default=user_config.scenarios_directory,
        help='override scenarios directory for stochastic problem')
        

    parser.add_argument('--standalone', '-m', action="store_true", 
        default=user_config.standalone,
        help='Make each multi-day commitment its own subprocess (helps with memory issues).')
    parser.add_argument('--output_prefix','-p', action="store_true",
        default=user_config.output_prefix,
        help='Prefix all results files with the process id (for a record of simulataneous solves)')


    debugging = parser.add_argument_group('Debugging tools')
    debugging.add_argument('--debugger',action="store_true",
        default=user_config.debugger,
        help='use pdb when an error is raised')
    debugging.add_argument('--problem_file',action="store_true",
        default=user_config.problem_file,
        help='flag to write the problem formulation to a problem.lp file')        
    parser.add_argument('--logging_level', type=int,
        default=user_config.logging_level,
        help='set the level of detail for logging')
    debugging.add_argument('--profile',action="store_true",
        default=False,
        help='run cProfile and output to minpower.profile')
    debugging.add_argument('--show_config', action='store_true',
        default=False, help='just show the configuration and quit')

    
    ts = parser.add_argument_group('Timeseries modifiers',
        'Alter the timeseries after parsing the data.')
    
    wind_modifier = ts.add_mutually_exclusive_group()
    wind_modifier.add_argument('--wind_multiplier', type=float,
        default=user_config.wind_multiplier,
        help='scale the wind power by this factor')
    wind_modifier.add_argument('--wind_capacity_factor', type=float,
        default=user_config.wind_capacity_factor,
        help='scale the wind power to match the capacity factor (as a percentage of peak load power)')
    
    ts.add_argument('--wind_error_multiplier', type=float,
        default=user_config.wind_error_multiplier,
        help='scale the wind power forecast error by this factor')
    ts.add_argument('--wind_forecast_adder', type=float,
        default=user_config.wind_forecast_adder,
        help='add a fixed amount (e.g. bias) to the wind power forecast')
    ts.add_argument('--load_multiplier', type=float,
        default=user_config.load_multiplier,
        help='scale the load power by this factor')
    ts.add_argument('--load_adder', type=float,
        default=user_config.load_adder,
        help='add a fixed amount to the load power')
    
    constraints = parser.add_argument_group('Ignore/relax constraints',
        'Ignore or relax sets of constraints to allow for feasible solutions.')
    constraints.add_argument('--ignore_minhours_constraints', 
        action="store_true", default=user_config.ignore_minhours_constraints,
        help='drop the min up/down time constraints on the generators')
    constraints.add_argument('--ignore_ramping_constraints', 
        action="store_true", default=user_config.ignore_ramping_constraints,
        help='drop the min ramping power constraints on the generators')
    constraints.add_argument('--ignore_pmin_constraints', 
        action="store_true", default=user_config.ignore_pmin_constraints,
        help='drop the min power constraints on the generators')
    constraints.add_argument('--pmin_multiplier', type=float,
        default=user_config.pmin_multiplier,
        help='scale the generator minimum power limits by this factor')
    constraints.add_argument('--ramp_limit_multiplier', type=float,
        default=user_config.ramp_limit_multiplier,
        help='scale the generator ramp power limits by this factor')


    
    parser.add_argument('--on_complete_script', type=str, 
        default=user_config.on_complete_script,
        help='run a script on completion of the minpower script')

    # NOTE - don't let defaults creep into this defenition
    # that makes resetting the defaults during testing very hard 
    
    return parser
