import pyomo.environ as pyo
from pyomo.opt import SolverFactory
from .test_utils import istest


@istest
def test_pyomo_duals():
    # create a model
    model = pyo.ConcreteModel()
    # Create a 'dual' suffix component on the instance
    # so the solver plugin will know which suffixes to collect
    model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    model.x = pyo.Var([1, 2], domain=pyo.NonNegativeReals)
    model.OBJ = pyo.Objective(expr=2 * model.x[1] + 3 * model.x[2])
    model.Constraint1 = pyo.Constraint(expr=3 * model.x[1] + 4 * model.x[2] >= 1)

    opt = SolverFactory("cbc")
    opt.solve(model)

    # make sure the dual is non-zero (constraint is binding)
    assert model.dual[model.Constraint1] != 0


@istest
def test_duals_mip():
    model = pyo.ConcreteModel()
    model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    model.x = pyo.Var([1, 2], domain=pyo.Boolean)
    model.y = pyo.Var([1, 2], domain=pyo.NonNegativeReals)
    # this problem is basically just two generators:
    # gen1 is cheap, but limited output
    # gen2 is more expensive
    model.OBJ = pyo.Objective(expr=2 * model.y[1] + 3 * model.y[2])
    model.Constraint1 = pyo.Constraint(expr=model.y[1] <= 50 * model.x[1])
    model.Constraint2 = pyo.Constraint(expr=model.y[2] <= 80 * model.x[2])
    model.Constraint3 = pyo.Constraint(expr=model.y[1] + model.y[2] == 100)

    opt = SolverFactory("cbc")
    opt.solve(model)

    # make sure the solution is what we'd expect (both gen need to run)
    assert model.x[1].value == True
    assert model.x[2].value == True

    # fix binary variables
    model.x[1].fixed = True
    model.x[2].fixed = True
    opt.solve(model)
    # make sure the dual is non-zero (constraint is binding)
    assert model.dual[model.Constraint3] != 0
