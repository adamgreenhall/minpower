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
    Pmin=0,

    costcurvestring=dict(
        generic=            '3000+25P+.005P^2',
        coal=               '3011+20.14P+.0084P^2',
        nuclear=            '5178+12.85P+.0014P^2',
        steamturbine=       '4793+42.75P+.0024P^2',
        combustionturbine=  '9586+42.75P+.0012P^2',
        wind=               '0'
        ),
    isControllable=True,
    power=None,
    
    Pmax=dict(
        generic=             500,
        coal=                550,
        nuclear=            1117, 
        nggt=                 90,
        ngcc=                420,
        
        ngst   = 450,
        ),
    
    minuptime=dict(
        generic=0,
        coal=24,
        nuclear=120,
        nggt=0,
        ngcc=6,
        
        ngst=4,
        ),
    
    mindowntime=dict(
        generic=0,
        coal=2,
        nuclear=18,
        nggt=0,
        ngcc=12,
        
        ngst=2,
        ),
#    ramprate_percent=dict(
#        generic=None,        
#        nuclear=0.10,
#        coal=0.30,
#        nggt=6.0,
#        ngcc=1.0,
#        
#        ngst=0.5,
#        ),
    
    fuelcost=dict(
        generic=    1,
        coal=       2.5,
        nuclear =   0.65,
        ngst=         5,
        ngcc=         5,
        nggt=         5,
        ),
    
    #from Henry Louie thesis
    startupcost=dict(
        generic=              0, #if kind not specified, no startup cost 
        coal=            107800,
        nuclear=         283500,
        ngst=             73500,
        nggt=             36750,
        wind=                 0,
        
        ngcc=             73500,
        )    
    
    )


cost_load_shedding = 100000000 #$/MWh

default_num_breakpoints=10
default_hours_commitment=24
default_hours_commitment_overlap=0
optimization_package='coopr' #'pulp'

optimization_solver='gurobi'
available_solvers = ['glpk','gurobi']#['glpk','gurobi','cplex']
logging_level= logging.INFO
