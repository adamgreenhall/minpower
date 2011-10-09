"""
Provide the defaults and data for other modules.
Specifically, the :class:`~powersystems.Generator` defaults
are provided by :data:`generator_defaults`.
"""
import logging

generator_kinds=[
    'generic',
    'baseload', 'coal','nuclear',
    'shoulder','naturalgas','steamturbine',
    'peaker','combustionturbine',
    'wind'
    ]

generator_defaults=dict(
    Pmin=0,
    Pmax=dict(
        generic=             500,
        baseload=           2000,
        coal=               2000,
        nuclear=            2000,
        shoulder=            500, 
        naturalgas=          500,
        steamturbine=       1050,
        peaker=              100, 
        combustionturbine=  2100,
        wind=                 80
        ),
    minuptime=dict(generic=0),
    mindowntime=dict(
        generic=0,
        baseload=2,coal=2,nuclear=18
        ),
    rampratemax=dict(
        generic=None,
        baseload=200,   coal=200,nuclear=100,
        shoulder=500, naturalgas=500, steamturbine=500,
        peaker=3000, combustionturbine=3000,
        wind=None
        ),
    costcurvestring=dict(
        generic=            '3000+25P+.005P^2',
        coal=               '3011+20.14P+.0084P^2',
        nuclear=            '5178+12.85P+.0014P^2',
        steamturbine=       '4793+42.75P+.0024P^2',
        combustionturbine=  '9586+42.75P+.0012P^2',
        wind=               '0'
        ),
    fuelcost=dict(
        generic=    1,
        coal=       2.5,
        naturalgas= 5
        ),
    startupcost=dict(
        #from Henry Louie thesis
        generic=              0, #if kind not specified, no startup cost 
        coal=            107800,
        nuclear=         283500,
        steamturbine=     73500,
        combustionturbine=36750,
        wind=                 0
        ),
    isControllable=True,
    power=None
    )


cost_loadshedding = 100000000 #$/MWh

default_num_breakpoints=5

optimization_package='coopr' #'pulp'

optimization_solver='gurobi'
available_solvers = ['glpk','gurobi']#,'cplex']
logging_level= logging.INFO
