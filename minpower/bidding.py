from commonscripts import * # update_attributes, pairwise
from optimization import value,OptimizationObject
from config import user_config
import re,weakref
from coopr.pyomo import Piecewise


class Bid(OptimizationObject):
    """
    A bid modeled by a polynomial or a set of piecewise points.
    """
    def __init__(self,
            polynomial='10P',
            bid_points=None,
            constant_term=0,
            owner=None,
            times=None,
            input_variable=0,
            min_input=0,
            max_input=1000,
            num_breakpoints=user_config.breakpoints,
            status_variable=True,
            fixed_input=False):
        update_attributes(self,locals(),exclude=['owner'])
        self._parent_problem=owner._parent_problem
        self.owner_id=str(owner)
        
        self.is_pwl = (self.bid_points is not None)
        self.is_linear = is_linear(self.polynomial)
        
        if not fixed_input: self.build_model()
    def build_model(self): 
        if self.bid_points is None:
            
            self.is_pwl = False
            self.constant_term = self.polynomial[0]
            
            if self.is_linear: return
            
            polynomial = list(self.polynomial)
            # use constant term in place of the 0th order term
            polynomial[0] = 0 
            
            self.add_variable('cost', index=self.times.set, low=0)
            def pw_rule(model,time,input_var): 
                return polynomial_value(polynomial, input_var)
            self.discrete_input_points=discretize_range(self.num_breakpoints,self.min_input,self.max_input)
            in_pts=dict((t,self.discrete_input_points) for t in self.times.set)

            pw_representation = Piecewise(
                self.times.set,
                self.get_variable('cost', time=None, indexed=True),
                self.input_variable(),
                f_rule=pw_rule,
                pw_pts=in_pts,
                pw_constr_type='LB',
                warn_domain_coverage = False, 
                # unless warn_domain_coverage is set, pyomo will complain
                # gen lower power bounds are set to zero (status trick) 
                # and Piecewise complains if Pmin>0,
               )
            
        else:
            # custom bid points
            self.is_linear = False
            self.is_pwl = True
            self.add_variable('cost',index=self.times.set,low=0)            

            self.discrete_input_points=[ bp[0] for bp in self.bid_points ]
            in_pts=dict((t,self.discrete_input_points) for t in self.times.set)
            mapping = dict(self.bid_points)
            def pw_rule(model,time,input_var): 
                # just the input->output points mapping in this case
                # see coopr/examples/pyomo/piecewise/example3.py
                return mapping[input_var]
                
            pw_representation=Piecewise(self.times.set,
                self.get_variable('cost',time=None,indexed=True),
                self.input_variable(),
                pw_pts=in_pts,
                pw_constr_type='LB',
                pw_repn='DCC', # the disagregated convex combination method 
                f_rule=pw_rule,
                warn_domain_coverage=False)

        pw_representation.name=self.iden()
        self.max_output = pw_rule(None,None, self.max_input)
        self._parent_problem().add_component_to_problem(pw_representation)
            
                
            
    def output(self, time=None, scenario=None, evaluate=False):
        status = self.status_variable(time, scenario)
        power = self.input_variable(time, scenario)        
        if evaluate: 
            status = value(status)
            power = value(power)

        if self.is_linear: 
            out = self.polynomial[1]*power
        else: 
            out = self.get_variable('cost', 
                time=time, scenario=scenario, indexed=True)
            if evaluate: out = value(out)
        
        if self.constant_term != 0:
            out += status * self.constant_term
            
        return out

    def output_true(self, input_var, force_linear=False): 
        '''true output value of bid'''
        input_val = value(input_var)
        
        if (self.is_pwl or force_linear) and not self.is_linear:
            if not self.is_pwl and self.bid_points is None:
                # construct the bid points
                bid_pt_outputs = map(lambda pt: polynomial_value(self.polynomial, pt), self.discrete_input_points)
                self.bid_points = zip(self.discrete_input_points, bid_pt_outputs)
            
            for A,B in pairwise(self.bid_points):
                if A[0]<=input_val<=B[0]: return get_line_value(A, B, input_val) + self.constant_term
        else: 
            return polynomial_value(self.polynomial, input_val)

    def output_incremental(self,input_var):
        input_val = value(input_var)
        if self.is_pwl:
            for A,B in pairwise(self.bid_points):
                if A[0]<=input_val<=B[0]: return get_line_slope(A,B)
        else:
            return polynomial_incremental_value(self.polynomial,value(input_var))

    def output_incremental_range(self):
        if self.is_pwl: 
            input_range = self.discrete_input_points
            output_range = [0]
            for A,B in pairwise(self.bid_points):
                output_range.append( get_line_slope(A,B) )
        else:
            input_range = np.arange(self.min_input, self.max_input, 1.0)
            output_range = [polynomial_incremental_value(self.polynomial,x) 
                for x in input_range]
        return input_range,output_range
    def __str__(self): return 'bid_{}'.format(self.owner_id)
    def iden(self,*a,**k): return 'bid_{}'.format(self.owner_id)

def is_linear(coefs):
    if len(coefs)<2: return True
    elif all(m==0 for m in coefs[2:]): return True
    else: return False

def discretize_range(num_breakpoints,minimum,maximum):
    step = (maximum-minimum)/float(num_breakpoints-1)
    return [x * step + minimum for x in range(int(num_breakpoints))]

def polynomial_value(multipliers,variable):
    """get the value of a polynomial"""
    def term(mult,var,order):
        if order>1: return mult*variable**order
        elif order==1: return mult*variable
        elif order==0: return mult
    return sum([term(mult,variable,order) for order,mult in enumerate(multipliers)])

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
    highest_order = max(max(order_multipliers.keys()),1) #order must be at least linear
    multipliers = [0]*(highest_order+1)
    for key,value in order_multipliers.items(): multipliers[key] = value
    
    return multipliers

def get_line_slope(A,B):
    xA,yA = A
    xB,yB = B
    return (yB-yA)*1.0/(xB-xA)


def get_line_value(A,B,x):
    '''
    take a pair of points and make a linear function
    get the value of the function at x
    see http://bit.ly/Pd4z4l
    '''
    xA,yA = A
    slope = get_line_slope(A,B)
    return slope*(value(x) - xA) + yA
