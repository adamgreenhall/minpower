from commonscripts import update_attributes
from optimization import value,OptimizationObject
from config import default_num_breakpoints
import re,weakref
from coopr.pyomo import Piecewise


class Bid(OptimizationObject):
    """
    Descibes a bid as modeled by :attr:model. Bids contain variables
    which are dependent on time while :class:`~bidding.PWLmodel` objects
    do not store time dependent information.
    
    :param model: model for the bid, either :class:`~bidding.PWLmodel`,
        :class:`~bidding.convexPWLmodel`, or :class:`~bidding.LinearModel`  
    :param times: the times the bids take place over 
    :param input_variable: input variable for owner at time periods of bid
    :param status_variable: status of owner at time periods of bid
    """
    def __init__(self,polynomial,owner,times,
                 input_variable=0,
                 min_input=0,
                 max_input=1000,
                 output_variable=None,
                 num_breakpoints=default_num_breakpoints,
                 status_variable=True,
                 fixed_input=False):
        update_attributes(self,locals(),exclude=['owner'])
        self.owner_id=str(owner)
        if not fixed_input: self.build_model(owner)
    def build_model(self,owner):
        def pw_rule(model,time,input_var): return polynomial_value(self.polynomial,input_var)
        self.discrete_input_points=discretize_range(self.num_breakpoints,self.min_input,self.max_input)
        in_pts=dict((t,self.discrete_input_points) for t in self.times.set)
        pw_representation=Piecewise(self.times.set,self.output_variable,self.input_variable,
                                               f_rule=pw_rule,
                                               pw_pts=in_pts,
                                               pw_constr_type='LB')
        pw_representation.name=self.iden()
        owner._parent_problem().add_component_to_problem(pw_representation)
                                               
    def output_true(self,input_var): 
        '''true output value of bid'''
        return polynomial_value(self.polynomial,value(input_var))
    def output_incremental(self,input_var):
        return polynomial_incremental_value(self.polynomial,value(input_var))
    def __str__(self): return 'bid_{}'.format(self.owner_id)
    def iden(self): return 'bid_{}'.format(self.owner_id)

def discretize_range(num_breakpoints,minimum,maximum):
    step = (maximum-minimum)/float(num_breakpoints)
    return [x * step + minimum for x in range(int(num_breakpoints))]

def polynomial_value(multipliers,variable):
    """get the value of a polynomial"""
    return sum([mult*variable**order for order,mult in enumerate(multipliers)])

def polynomial_incremental_value(multipliers,variable):
    """get the incremental value of a polynomial"""
    return sum([(mult*order*variable**(order-1) if order>0 else 0) for order,mult in enumerate(multipliers)])

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
        if not s: return 1
        elif s == '-': return -1
        elif s == '+': return 1
        return eval(s)

    def parse_p(s,powerPattern):
        '''Parse the power part of a polynomial string term'''
        if not s: return 0
        multipliers = powerPattern.findall(s)[0]
        if not multipliers: return 1
        return int(multipliers)
    s=str(s).replace(' ','') #remove all whitespace from string
    m = re.search('[a-zA-Z]+', s) 
    try: varLetter=m.group(0)
    except AttributeError: varLetter='P'
    termPattern = re.compile('([+-]?\d*\.?\d*)\**({var}?\^?\d?)'.format(var=varLetter))
    powerPattern = re.compile('{var}\^?(\d)?'.format(var=varLetter))
    order_multipliers = {}
    
    for n,p in termPattern.findall(s):
        n,p = n.strip(),p.strip()
        if not n and not p: continue
        n,p = parse_n(n),parse_p(p,powerPattern)
        if order_multipliers.has_key(p): order_multipliers[p] += n
        else: order_multipliers[p] = n
    highest_order = max(order_multipliers.keys())
    multipliers = [0]*(highest_order+1)
    for key,value in order_multipliers.items(): multipliers[key] = value
    
    return multipliers