"""
Provide the defaults and configuration for other modules.
`user_config` is treated as a global in minpower.
"""
import os
from ConfigParser import SafeConfigParser
from commonscripts import DotDict, joindir

generator_kinds=[
    'generic',
    'coal','nuclear',
    'ngst','ngcc',
    'nggt',
    'wind',
    'chp'
    ]

generator_defaults=dict(
    Pmin=dict(generic=0,wind=0),

    costcurvestring=dict(
        generic=            '3000+25P+.005P^2',
        coal=               '3011+20.14P+.0084P^2',
        nuclear=            '5178+12.85P+.0014P^2',
        steamturbine=       '4793+42.75P+.0024P^2',
        combustionturbine=  '9586+42.75P+.0012P^2',
        wind=               '0'
        ),
    is_controllable=dict(generic=True,wind=False),
    power=dict(generic=None),

    Pmax=dict(
        generic=             500,
        coal=                550,
        nuclear=            1117,
        nggt=                 90,
        ngcc=                420,
        ngst   =             550,#assume equal to coal fired steam
        wind   =             100,
        ),

    minuptime=dict(
        generic=0,
        coal=24,
        nuclear=120,
        nggt=0,
        ngcc=6,
        ngst=24, #assume equal to coal fired steam
        wind=0,
        ),

    mindowntime=dict(
        generic=0,
        coal=2,
        nuclear=18,
        nggt=0,
        ngcc=12,
        ngst=12,#assume equal to coal fired steam
        wind=0,
        ),

    fuelcost=dict(
        generic=    1,
        coal=       2.0,   #from EIA national average coal price: http://www.eia.gov/electricity/monthly/
        ngst=       4.0,   #midrange forecast from NWPP plan: http://www.nwcouncil.org/energy/powerplan/6/
        ngcc=       4.0,
        nggt=       4.0,
        nuclear =   0.65,  #from NWPP plan - Table I-34: Forecast nuclear fuel prices (2006$/MMBtu)
        wind=       0,
        ),


    startupcost=dict(
        generic=              0, #if kind not specified, no startup cost
##from Henry Louie thesis
#        coal=            107800,
#        nuclear=         283500,
#        ngst=             73500,
#        nggt=             36750,
#        wind=                 0,
#        ngcc=             73500, #assume same as NG ST
##from WECC Planning Study, via B.Palmintier - http://www.eia.gov/oiaf/beck_plantcosts/
        coal=     3581,
        nuclear=100000,
        ngst   =  3581,
        nggt   =  7811,
        ngcc   =  9250,
        wind   =     0,
        )
    )


parser = SafeConfigParser()
parser.read([
    # the minpower default set, from the minpower/configuration directory 
    joindir(os.path.split(__file__)[0], 'configuration/minpower.cfg'), 
    # the user's overrides, from the home directory
    os.path.expanduser('~/minpower.cfg'),
    os.path.expanduser('~/.minpowerrc'),
    ],
    # add another override in the specific case directory??
    )


m = 'minpower'
user_config = DotDict(dict(
    duals = parser.getboolean(m, 'duals'),
    breakpoints = parser.getint(m, 'breakpoints'),
    hours_commitment = parser.getint(m, 'hours_commitment'),
    hours_overlap = parser.getint(m, 'hours_overlap'),
    
    cost_load_shedding = parser.getfloat(m, 'cost_load_shedding'),
    cost_wind_shedding = parser.getfloat(m, 'cost_wind_shedding'),
    dispatch_decommit_allowed = \
        parser.getboolean(m, 'dispatch_decommit_allowed'),
    solver = parser.get(m, 'solver'),
    mipgap = parser.getfloat(m, 'mipgap'), 

    reserve_fixed = parser.getfloat(m, 'reserve_fixed'),
    reserve_load_fraction = \
        parser.getfloat(m, 'reserve_load_fraction'),

    faststart_resolve = parser.getboolean(m, 'faststart_resolve'),

    visualization = parser.getboolean(m, 'visualization'),
    logging_level = parser.getint(m, 'logging_level'),
    problem_file = parser.getboolean(m, 'problem_file'),
    output_prefix = parser.getboolean(m, 'output_prefix'),
    debugger = parser.getboolean(m, 'debugger'),


    scenarios = parser.getint(m, 'scenarios'),
    deterministic_solve = parser.getboolean(m, 'deterministic_solve'),
    perfect_solve = parser.getboolean(m, 'perfect_solve'),
    scenarios_directory = parser.get(m, 'scenarios_directory'),
    
    standalone = parser.getboolean(m, 'standalone'),

    wind_forecast_adder = parser.getfloat(m, 'wind_forecast_adder'),
    wind_multiplier = parser.getfloat(m, 'wind_multiplier'),
    load_multiplier = parser.getfloat(m, 'load_multiplier'),

    pmin_multiplier = parser.getfloat(m, 'pmin_multiplier'),
    ramp_limit_multiplier = parser.getfloat(m, 'ramp_limit_multiplier'),

    ignore_minhours_constraints = parser.getboolean(
        m, 'ignore_minhours_constraints'),
    ignore_ramping_constraints = parser.getboolean(
        m, 'ignore_ramping_constraints'),
    ignore_pmin_constraints = parser.getboolean(
        m, 'ignore_pmin_constraints'),
    
    on_complete_script = parser.get(m, 'on_complete_script'),
    
    # HACKs to help out resetting the config in testing
    directory = parser.get(m, 'directory'),
    store_filename = parser.get(m, 'store_filename'),
    ))

available_solvers = []
for solver in parser.options('available_solvers'):
  if parser.getboolean('available_solvers', solver):
      available_solvers.append(solver)
