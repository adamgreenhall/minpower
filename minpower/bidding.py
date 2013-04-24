import pandas as pd
import numpy as np
from commonscripts import update_attributes, pairwise, set_trace
from optimization import value, OptimizationObject
from config import user_config
import re
from coopr import pyomo
from coopr.pyomo.base import piecewise


class Bid(OptimizationObject):
    """
    A bid modeled by a polynomial or a set of piecewise points.
    """
    def __init__(self,
                 polynomial='10P',
                 bid_points=None,
                 output_name='cost',
                 constant_term=0,
                 owner=None,
                 times=None,
                 input_variable=0,
                 min_input=0,
                 max_input=1000,
                 num_breakpoints=user_config.breakpoints,
                 status_variable=True,
                 fixed_input=False,
                 pw_repn=None,
                 pw_constr_type='LB',
                 ):
        update_attributes(self, locals(), exclude=['owner'])
        self._parent_problem = owner._parent_problem
        self.owner_id = str(owner)

        self.is_pwl = (self.bid_points is not None)
        self.is_linear = is_linear(self.polynomial)

        if not fixed_input:
            self.build_model()

    def build_model(self):
        if self.bid_points is None:

            self.is_pwl = False
            self.constant_term = self.polynomial[0]

            if self.is_linear:
                return

            polynomial = list(self.polynomial)
            # use constant term in place of the 0th order term
            polynomial[0] = 0

            self.add_variable(self.output_name, index=self.times.set, low=0)

            def pw_rule(model, time, input_var):
                return polynomial_value(polynomial, input_var)
            self.discrete_input_points = discretize_range(
                self.num_breakpoints, self.min_input, self.max_input)
            in_pts = dict(
                (t, self.discrete_input_points) for t in self.times.set)

            pw_representation = pyomo.Piecewise(
                self.times.set,
                self.get_variable(self.output_name, time=None, indexed=True),
                self.input_variable(),
                f_rule=pw_rule,
                pw_pts=in_pts,
                pw_constr_type=self.pw_constr_type,
                warn_domain_coverage=False,
                # unless warn_domain_coverage is set, pyomo will complain
                # gen lower power bounds are set to zero (status trick)
                # and Piecewise complains if Pmin>0,
            )

        else:
            # custom bid points
            self.is_linear = False
            self.is_pwl = True
            self.max_input = self.bid_points.indvar.max()
            self.min_input = self.bid_points.indvar.min()
            self.bid_points = drop_dup_slopes(self.bid_points)
            self.add_variable(self.output_name, index=self.times.set, low=0)
            self.discrete_input_points = self.bid_points.indvar.values.tolist()
            in_pts = dict(
                (t, self.discrete_input_points) for t in self.times.set)
            mapping = self.bid_points.set_index('indvar').to_dict()['depvar']

            def pw_rule_points(model, time, input_var):
                # just the input->output points mapping in this case
                # see coopr/examples/pyomo/piecewise/example3.py
                return mapping[input_var]

            pw_representation = pyomo.Piecewise(self.times.set,
                self.get_variable(self.output_name, time=None, indexed=True),
                self.input_variable(),
                pw_pts=in_pts,
                pw_constr_type=self.pw_constr_type,
                pw_repn='DCC' if self.pw_repn is None else self.pw_repn,
                # use a default of the disagregated convex combination method
                f_rule=pw_rule_points,
                warn_domain_coverage=False)

        pw_representation.name = self.iden()
        self.max_output = pw_representation._f_rule(None, None, self.max_input)
        self._parent_problem().add_component_to_problem(pw_representation)

    def output(self, time=None, scenario=None, evaluate=False):
        status = self.status_variable(time, scenario)
        power = self.input_variable(time, scenario)
        if evaluate:
            status = value(status)
            power = value(power)

        if self.is_linear:
            out = self.polynomial[1] * power
        else:
            out = self.get_variable(self.output_name,
                time=time, scenario=scenario, indexed=True)
            if evaluate:
                out = value(out)

        if self.constant_term != 0:
            out += status * self.constant_term

        return out

    def output_true(self, input_var, force_linear=False):
        '''true output value of bid'''
        input_val = value(input_var)

        if (self.is_pwl or force_linear) and not self.is_linear:
            if not self.is_pwl and self.bid_points is None:
                # construct the bid points
                bid_pt_outputs = map(lambda pt: polynomial_value(
                    self.polynomial, pt), self.discrete_input_points)
                self.bid_points = zip(
                    self.discrete_input_points, bid_pt_outputs)

            for A, B in pairwise(self.bid_points.values.tolist()):
                if A[0] <= input_val <= B[0]:
                    return get_line_value(A, B, input_val) + self.constant_term
            raise ValueError(
                'value {} was not within piecewise specification.\n{}'.format(
                input_val, self.bid_points))
        else:
            return polynomial_value(self.polynomial, input_val)

    def output_incremental(self, input_var):
        input_val = value(input_var)
        if self.is_pwl:
            for A, B in pairwise(self.bid_points):
                if A[0] <= input_val <= B[0]:
                    return get_line_slope(A, B)
        else:
            return polynomial_incremental_value(self.polynomial, value(input_var))

    def output_incremental_range(self):
        if self.is_pwl:
            input_range = self.discrete_input_points
            output_range = [0]
            for A, B in pairwise(self.bid_points):
                output_range.append(get_line_slope(A, B))
        else:
            input_range = np.arange(self.min_input, self.max_input, 1.0)
            output_range = [polynomial_incremental_value(self.polynomial, x)
                            for x in input_range]
        return input_range, output_range

    def __str__(self):
        return 'curve_{}_{}'.format(self.output_name, self.owner_id)

    def iden(self, *a, **k):
        return 'curve_{}_{}'.format(self.output_name, self.owner_id)


def is_linear(coefs):
    result = False
    if coefs is None:
        result = False
    else:
        if len(coefs) < 2:
            result = True
        elif all(m == 0 for m in coefs[2:]): result = True
        else:
            result = False
    return result


def discretize_range(num_breakpoints, minimum, maximum):
    step = (maximum - minimum) / float(num_breakpoints - 1)
    return [x * step + minimum for x in range(int(num_breakpoints))]


def polynomial_value(multipliers, variable):
    """get the value of a polynomial"""
    def term(mult, var, order):
        if order > 1:
            return mult * variable ** order
        elif order == 1:
            return mult * variable
        elif order == 0:
            return mult
    return sum([term(mult, variable, order) for order, mult in enumerate(multipliers)])


def polynomial_incremental_value(multipliers, variable):
    """get the incremental value of a polynomial"""
    return sum([(mult * order * variable ** (order - 1) if order > 0 else 0) for order, mult in enumerate(multipliers)])


def parse_polynomial(s):
    """
    Parse a string into a set of multipliers.
    Heavily adapted from `<http://bit.ly/polynomialParse>`_.

    Can handle simple polynomials (addition and subtraction):

    >>> parse_polynomial('7x^2 + 6x - 5')
    [-5, 6, 7]

    or with the explicit * multiplier:

    >>> parse_polynomial('7*P^2 + 6*P - 5')
    [-5, 6, 7]

    or even with the terms in some random order:

    >>> parse_polynomial('6*P - 5 + 7*P^2')
    [-5, 6, 7]
    """

    def parse_n(s):
        '''Parse the number part of a polynomial string term'''
        if not s:
            return 1
        elif s == '-':
            return -1
        elif s == '+':
            return 1
        return float(eval(s))

    def parse_p(s, powerPattern):
        '''Parse the power part of a polynomial string term'''
        if not s:
            return 0
        multipliers = powerPattern.findall(s)[0]
        if not multipliers:
            return 1
        return int(multipliers)
    s = str(s).replace(' ', '')  # remove all whitespace from string
    m = re.search('[a-zA-Z]+', s)
    try:
        varLetter = m.group(0)
    except AttributeError:
        varLetter = 'P'
    termPattern = re.compile(
        '([+-]?\d*\.?\d*)\**({var}?\^?\d?)'.format(var=varLetter))
    powerPattern = re.compile('{var}\^?(\d)?'.format(var=varLetter))
    order_multipliers = {}

    for n, p in termPattern.findall(s):
        n, p = n.strip(), p.strip()
        if not n and not p:
            continue
        n, p = parse_n(n), parse_p(p, powerPattern)
        if p in order_multipliers:
            order_multipliers[p] += n
        else:
            order_multipliers[p] = n
    highest_order = max(
        max(order_multipliers.keys()), 1)  # order must be at least linear
    multipliers = [0] * (highest_order + 1)
    for key, value in order_multipliers.items():
        multipliers[key] = value

    return multipliers


def get_line_slope(A, B):
    xA, yA = A
    xB, yB = B
    return (yB - yA) * 1.0 / (xB - xA)


def get_line_value(A, B, x):
    '''
    take a pair of points and make a linear function
    get the value of the function at x
    see http://bit.ly/Pd4z4l
    '''
    xA, yA = A
    slope = get_line_slope(A, B)
    return slope * (value(x) - xA) + yA

def drop_dup_slopes(df):
    slopes = pd.Series(df.depvar.diff() / df.indvar.diff(), name='slope')
    if len(slopes.unique()) == len(df): return df
    out = df.ix[[0]].copy()
    for i, row in df.iterrows():
        if i == 0: continue
        if slopes[i] != slopes[i - 1]:
            out = out.append(row)
    else:
        if slopes[i] == slopes[i-1]:
            out = out.append(row)
    return out
    
class TwoVarPW(OptimizationObject):
    def __init__(self, times, owner,
        inputA, inputB,
        pointsA, pointsB, 
        pointsOut,
        output_name='cost',
        output_var=None,
        status_variable=True
        ):
        '''
        implements a general piecewise linear formulation with two variables
        called the "rectangle method" and based on the paper:
        D'Ambrosio, Lodi, Martello 2009
        
        pointsOut is a Series with a MultiIndex, by both pointsA and pointsB
        '''
        self.name = '{}_{}'.format(output_name, str(owner))
        self.output_var = output_var
        self.output_name = output_name
        self._parent_problem = owner._parent_problem
        self.owner_id = str(owner)
        self.is_pwl = True
        self.is_linear = False


        for time in times:
            self.build_constraints(time, inputA(time), inputB(time), 
                pointsA, pointsB, pointsOut, self.output_var(time))

    def output(self, time):
        return self.output_var(time)

    def add_component(self, comp, time):
        comp.name += '_' + self.iden(time)
        self._parent_problem().add_component_to_problem(comp)

    def build_constraints(self, time, inputA, inputB,
        pointsA, pointsB, pointsOut, outputVar):
        '''construct the PW variables and constraints for a single time'''

        n = len(pointsA)
        m = len(pointsB)
        a_index = range(n)
        b_index = range(m)
        a_index_short = range(n-1)
        b_index_short = range(m-1)

        binaryA = self.add_variable('binaryA_{}'.format(time),
            index=a_index_short, kind='Boolean')
        fractionA = self.add_variable('fractionA_{}'.format(time),
            index=a_index, kind='NonNegativeReals')

        # eqn4
        self.add_constraint('bin_sumA', time, 
            sum(binaryA[i] for i in a_index_short) == 1)
        
        # eqn5 
        self.add_constraint_set('Afrac_max_{}'.format(time), a_index, 
            lambda model, i: fractionA[i] <= \
                (binaryA[i-1] if 0 < i else 0) + \
                (binaryA[i] if i < n-1 else 0))

        # eqn6
        self.add_constraint('Afrac_sum', time, 
            sum(fractionA[i] for i in a_index) == 1)

        # eqn7
        self.add_constraint('sumX', time, 
            inputA == sum(fractionA[i] * pointsA[i] for i in a_index))

        binaryB = self.add_variable('binaryB_{}'.format(time),
            index=b_index_short, kind='Boolean')
        proportionB = self.add_variable('proportionB_{}'.format(time),
            index=b_index_short, kind='NonNegativeReals')
        
        # eqn11
        self.add_constraint('bin_sumB', time, 
            sum(binaryB[j] for j in b_index_short) == 1)
            
        # eqn23
        self.add_constraint('sumY', time, 
            inputB == sum(binaryB[j] * pointsB[j] + \
                proportionB[j] * (pointsB[j+1] - pointsB[j]) \
                for j in b_index_short)
        )

        # eqn24
        self.add_constraint_set('Bprop_max_{}'.format(time), b_index_short, 
            lambda model, j: proportionB[j] <= binaryB[j])
        
        # setup K_{ij}
        def delta(i, j): 
            return pointsOut.ix[(pointsA[i], pointsB[j+1])] - \
                   pointsOut.ix[(pointsA[i], pointsB[j])]
        def K(i, j): return min(delta(i, j), delta(i+1, j))

        bigM = 1e9
        def summationTerm(j): return sum(fractionA[k] * \
            pointsOut.ix[(pointsA[k], pointsB[j])] for k in a_index)
        
        # eqn25
        def output_upper_rule(model, i, j):
            return outputVar <= summationTerm(j) + \
                proportionB[j] * K(i, j) + \
                bigM * (2 - binaryA[i] - binaryB[j])
        self.add_component(pyomo.Constraint(a_index_short, b_index_short, 
            rule=output_upper_rule,
            name='output_upper'), time)

        # eqn26
        def output_lower_rule(model, i, j):
            return outputVar >= summationTerm(j) + \
                proportionB[j] * K(i, j) + \
                -1 * bigM * (2 - binaryA[i] - binaryB[j])
        self.add_component(pyomo.Constraint(a_index_short, b_index_short,
            rule=output_lower_rule,
            name='output_lower'), time)

        # label the special ordered sets
        self.add_component(piecewise.SOSConstraint(
            name='A_sos1', var=binaryA, sos=1), time)
        self.add_component(piecewise.SOSConstraint(
            name='A_sos2', var=fractionA, sos=2), time)
        self.add_component(piecewise.SOSConstraint(
            name='B_sos1', var=binaryB, sos=1), time)
        return
        

    def __str__(self):
        return 'curve_{}_{}'.format(self.output_name, self.owner_id)

    def iden(self, time):
        return 'curve_{}_{}_{}'.format(self.output_name, self.owner_id, str(time))
