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

user_config = DotDict(dict(
    duals = parser.getboolean('minpower', 'duals'),
    breakpoints = parser.getint('minpower', 'breakpoints'),
    hours_commitment = parser.getint('minpower', 'hours_commitment'),
    hours_overlap = parser.getint('minpower', 'hours_overlap'),
    
    cost_load_shedding = parser.getfloat('minpower', 'cost_load_shedding'),
    dispatch_decommit_allowed = \
        parser.getboolean('minpower', 'dispatch_decommit_allowed'),
    solver = parser.get('minpower', 'solver'),
    mipgap = parser.getfloat('minpower', 'mipgap'), 

    reserve_fixed = parser.getfloat('minpower', 'reserve_fixed'),
    reserve_load_fraction = \
        parser.getfloat('minpower', 'reserve_load_fraction'),

    faststart_resolve = parser.getboolean('minpower', 'faststart_resolve'),

    visualization = parser.getboolean('minpower', 'visualization'),
    logging_level = parser.getint('minpower', 'logging_level'),
    problem_file = parser.getboolean('minpower', 'problem_file'),
    output_prefix = parser.getboolean('minpower', 'output_prefix'),
    debugger = parser.getboolean('minpower', 'debugger'),


    scenarios = parser.getint('minpower', 'scenarios'),
    deterministic_solve = parser.getboolean('minpower', 'deterministic_solve'),
    perfect_solve = parser.getboolean('minpower', 'perfect_solve'),
    scenarios_directory = parser.get('minpower', 'scenarios_directory'),
    
    standalone = parser.getboolean('minpower', 'standalone'),

    wind_multiplier = parser.getfloat('minpower', 'wind_multiplier'),

    ignore_minhours_constraints = parser.getboolean(
        'minpower', 'ignore_minhours_constraints'),
    ignore_ramping_constraints = parser.getboolean(
        'minpower', 'ignore_ramping_constraints'),
    ignore_pmin_constraints = parser.getboolean(
        'minpower', 'ignore_pmin_constraints'),

    # HACKs to help out resetting the config in testing
    directory = parser.get('minpower', 'directory'),
    store_filename = parser.get('minpower', 'store_filename'),
    ))

available_solvers = []
for solver in parser.options('available_solvers'):
  if parser.getboolean('available_solvers', solver):
      available_solvers.append(solver)
