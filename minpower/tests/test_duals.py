import pyomo.environ as pyo
from pyomo.opt import SolverFactory
from .test_utils import istest


@istest
def test_pyomo_duals():
    # Create a solver
    opt = SolverFactory("cbc")

    # create a model
    model = pyo.ConcreteModel()
    model.x = pyo.Var([1, 2], domain=pyo.NonNegativeReals)
    model.OBJ = pyo.Objective(expr=2 * model.x[1] + 3 * model.x[2])
    model.Constraint1 = pyo.Constraint(expr=3 * model.x[1] + 4 * model.x[2] >= 1)

    # Create a 'dual' suffix component on the instance
    # so the solver plugin will know which suffixes to collect
    model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    opt.solve(model)  # also load results to model

    # make sure the dual is non-zero (constraint is binding)
    assert model.dual[model.Constraint1] != 0
