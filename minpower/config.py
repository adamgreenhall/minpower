"""
Provide the defaults and data for other modules.
Specifically, the :class:`~powersystems.Generator` defaults
are provided by :data:`generator_defaults`.
"""
import logging

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


cost_load_shedding = 1000 #$/MWh

default_num_breakpoints=11
default_hours_commitment=24
default_hours_commitment_overlap=0

optimization_solver='glpk'
available_solvers = ['glpk','gurobi']#['glpk','gurobi','cplex']
logging_level= logging.INFO