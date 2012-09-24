from commonscripts import update_attributes,frange,pairwise
from optimization import value,OptimizationObject
from config import default_num_breakpoints
import re,weakref
from coopr.pyomo import Piecewise

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
from scipy import linspace, polyval, polyder, interp, poly1d
<<<<<<< HEAD
#from pylab import plot,show,savefig,xlabel,ylabel
=======
=======
from scipy import linspace, polyval, polyder, interp, poly1d, optimize
>>>>>>> fix for setting breakpoints post init. convex polynomial price visualization now shows linearization effects (stepwise ICs)
=======
from scipy import linspace, polyval, polyder, interp, poly1d
>>>>>>> got rid of unneeded scipy imports

#import matplotlib
#from sys import platform as osname
#if osname=='darwin': matplotlib.use('macosx') #avoid popups when using matploblib to savefig on MacOSX
try: from pylab import plot,savefig,xlabel,ylabel
except ImportError: pass #shouldnt affect normal operation

>>>>>>> working coopr and pulp mix
import re
=======
>>>>>>> use native pyomo.Piecewise to do bidding linearization models

class Bid(OptimizationObject):
    """
    Descibes a bid as modeled by :attr:model. Bids contain variables
    which are dependent on time while :class:`~bidding.PWLmodel` objects
    do not store time dependent information.
    
    :param model: model for the bid, either :class:`~bidding.PWLmodel`,
        :class:`~bidding.convexPWLmodel`, or :class:`~bidding.LinearModel`  
    :param times: the times the bids take place over 
    :param input_variable: input variable method for owner
    :param status_variable: status variable method for owner
    """
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD

    def __init__(self,model,iden):
        vars(self).update(locals())

        #add time variables
<<<<<<< HEAD
        self.segmentsActive,self.fractionsBP=self.model.addTimeVars(self.iden)
    def output(self,solution=None): return self.model.output(self.fractionsBP,solution)
=======
        self.segmentsActive,self.fractionsBP=self.model.add_timevars(self.iden)
<<<<<<< HEAD
    def output(self,inputVar): return self.model.output(self.fractionsBP,inputVar)
>>>>>>> added linear bid model. much cleaner formulation.
=======
    def output(self,inputVar): 
        return self.model.output(self.fractionsBP,inputVar)
>>>>>>> add status to the new linearization constraints
=======
    def __init__(self,model,inputvar,iden,statusvar=True):
<<<<<<< HEAD
        vars(self).update(locals())        
    def output(self): 
        return self.model.output(self.variables,self.iden)
<<<<<<< HEAD
>>>>>>> cleaner handling of different bid models. fix for the convex bid model, due to confusion from ugly code.
    def trueOutput(self,input): return self.model.trueOutput(input)
    def incOutput(self,input):  return self.model.incOutput(input)
=======
    def trueOutput(self,input_val): return self.model.trueOutput(input_val)
    def incOutput(self,input_val):  return self.model.incOutput(input_val)
>>>>>>> added user breakpoint control by moving buildCostModel into add_timevars
=======
=======
    def __init__(self,model,owner_iden,time_iden,input_var=0,status_var=True):
>>>>>>> first draft of refactor
=======
    def __init__(self,model,time,owner_iden,time_iden,input_var=0,status_var=True):
<<<<<<< HEAD
>>>>>>> first working pass through solver (results still needs major rework
        update_attributes(self,locals())
=======
        update_attributes(self,locals(),exclude=['input_var','status_var'])
>>>>>>> redo of bid, bid.model input and status variable handling
        self.init_optimization()
<<<<<<< HEAD
        self.variables['input'] = input_var
        self.variables['status']= status_var 
<<<<<<< HEAD
<<<<<<< HEAD
    def output_true(self,input_val): return self.model.output_true(input_val)
    def output_incremental(self,input_val):  return self.model.output_incremental(input_val)
<<<<<<< HEAD
>>>>>>> refactored powersystems. moving on to bidding
    def plotDeriv(self,**kwargs): return self.model.plotDeriv(**kwargs)
=======
=======
=======
=======
        self.variables=dict(input=input_var,status=status_var)
>>>>>>> update docs
        self.name='bid_'+owner_iden+time_iden
>>>>>>> major overahual on setting up variables/constraints directly to the parent problem. this allows the use of sets, variable lists. still need to cleanup (including dual values).
    def output_true(self,input_val): 
        '''true output value of bid'''
        return self.model.output_true(input_val)
    def output_incremental(self,input_val):
        '''incremental output value of bid'''
        return self.model.output_incremental(input_val)
>>>>>>> doc overhaul bidding
    def plot_derivative(self,**kwargs): return self.model.plot_derivative(**kwargs)
>>>>>>> first draft of refactor
    def plot(self,P=None,filename=None,showPW=False):
        plotted=self.model.plot(P,showPW=showPW)
        if filename is not None: savefig(filename)
        return plotted
    
    def create_variables(self):
        '''Call the :attr:model and get any additional variables from it.'''
        variable_parameters=self.model.get_variable_params(self.input(),
                                                           self.status(),
                                                           self.owner_iden,self.time_iden)
        for vp in variable_parameters: self.add_variable(**vp)
    def create_constraints(self):
        '''
        Create the constraints for a bid by calling its model's :meth:`get_time_constraints` method.
        :return: a dictionary of the bid's constraints 
        '''
        constraintD=self.model.get_time_constraints(self)
        for nm,expr in constraintD.items(): self.add_constraint(nm,self.time,expr)
    def output(self,evaluate=False): return self.model.output(self,evaluate)  
    def input(self,evaluate=False):  return self.variables['input'] if not evaluate else value(self.variables['input'])
    def status(self,evaluate=False): return self.variables['status'] if not evaluate else value(self.variables['status'])
    def __str__(self): return 'bid{t}'.format(t=str(self.time))
    def iden(self,*args): return 'bid{t}'.format(t=str(self.time))
=======
    def __init__(self,polynomial,owner,times,
                 input_variable=0,
                 min_input=0,
                 max_input=1000,
                 num_breakpoints=default_num_breakpoints,
                 status_variable=True,
                 fixed_input=False):
=======
    def __init__(self,
            polynomial='10P',
            bid_points=None,
            constant_term=0,
            owner=None,
            times=None,
            input_variable=0,
            min_input=0,
            max_input=1000,
            num_breakpoints=default_num_breakpoints,
            status_variable=True,
            fixed_input=False):
>>>>>>> custom specification of pwl bid points
        update_attributes(self,locals(),exclude=['owner'])
        self._parent_problem=owner._parent_problem
        self.owner_id=str(owner)
        
        self.is_pwl = (self.bid_points is not None)
        
        if not fixed_input: self.build_model()
    def build_model(self): 
        if self.bid_points is None:
            self.is_linear=is_linear(self.polynomial)
            self.is_pwl = False
            if self.is_linear: return

            self.add_variable('cost',index=self.times.set,low=0)
            def pw_rule(model,time,input_var): return polynomial_value(self.polynomial,input_var)
            self.discrete_input_points=discretize_range(self.num_breakpoints,self.min_input,self.max_input)
            in_pts=dict((t,self.discrete_input_points) for t in self.times.set)
            pw_representation=Piecewise(self.times.set,self.output(),self.input_variable(),
                                           f_rule=pw_rule,
                                           pw_pts=in_pts,
                                           pw_constr_type='LB')
            
        else:
            # custom bid points
            self.is_linear = False
            self.is_pwl = True
            self.add_variable('cost',index=self.times.set,low=0)            
            # pw_rule = dict( [ (i, lambda x: get_line_value(pA, pB, x)) for i,(pA,pB) in enumerate(pairwise(self.bid_points))] )

            self.discrete_input_points=[ bp[0] for bp in self.bid_points ]
            in_pts=dict((t,self.discrete_input_points) for t in self.times.set)
            mapping = dict(self.bid_points)
            def pw_rule(model,time,input_var): 
                # just the input->output points mapping in this case  - see coopr/examples/pyomo/piecewise/example3.py
                return mapping[input_var]
                
            pw_representation=Piecewise(self.times.set,
                                          self.get_variable('cost',time=None,indexed=True),
                                          self.input_variable(),
                                          pw_pts=in_pts,
                                          pw_constr_type='LB',
                                          pw_repn='DCC', # the disagregated convex combination method 
                                          f_rule=pw_rule)

        pw_representation.name=self.iden()
        self._parent_problem().add_component_to_problem(pw_representation)
        
            
                
            
    def output(self,time=None,evaluate=False):
        if self.is_linear: 
            if evaluate: 
                out = value(self.status_variable(time))*self.polynomial[0]+self.polynomial[1]*value(self.input_variable(time))
            else:
                out = self.status_variable(time)*self.polynomial[0]+self.polynomial[1]*self.input_variable(time)
        else: 
            out = self.get_variable('cost',time=time,indexed=True)
            if evaluate: out = value(out)
        
        if self.is_pwl and self.constant_term!=0:
            const = self.status_variable(time)*self.constant_term
            if evaluate: const = value(const)
            out += const
            
        return out
    def output_true(self,input_var): 
        '''true output value of bid'''
        input_val = value(input_var)
        if self.is_pwl:
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
            input_range=[x for x in frange(self.min_input,self.max_input+1)]
            output_range=[polynomial_incremental_value(self.polynomial,x) for x in input_range]
        return input_range,output_range
    def __str__(self): return 'bid_{}'.format(self.owner_id)
<<<<<<< HEAD
    def iden(self): return 'bid_{}'.format(self.owner_id)
>>>>>>> use native pyomo.Piecewise to do bidding linearization models
=======
    def iden(self,*a,**k): return 'bid_{}'.format(self.owner_id)

def is_linear(multipliers):
    if len(multipliers)<2: return True
    elif all(m==0 for m in multipliers[2:]): return True
    else: return False
>>>>>>> debugging linear case - dont use SOS2 constraints to char linear problem

def discretize_range(num_breakpoints,minimum,maximum):
    step = (maximum-minimum)/float(num_breakpoints)
    return [x * step + minimum for x in range(int(num_breakpoints))]

def polynomial_value(multipliers,variable):
    """get the value of a polynomial"""
    def term(mult,var,order):
        if order>1: return mult*variable**order
        elif order==1: return mult*variable
        elif order==0: return mult
    return sum([term(mult,variable,order) for order,mult in enumerate(multipliers)])

<<<<<<< HEAD
        constraints['oneActiveSegment '+iden]= sum(S)== status_var 
        constraints['fractionSums '+iden]    = sum(F) == status_var 
        constraints['computeInput '+iden]    = input_var == sum( elementwiseMultiply(F,self.bp_inputs) )
        constraints['firstSegment '+iden]    = F[0]<=S[0]
        constraints['lastSegment '+iden]     = F[-1]<=S[-1]
        for b in range(1,self.num_breakpoints-1): 
            name='midSegment {iden} b{bnum}'.format(iden=iden,bnum=b)
            constraints[name]                = ( F[b] <= sum([S[b-1],S[b]]) )
        return constraints
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    def output(self,F,solution=None): 
        return sum( [ value(Fval,solution)*self.bpOutputs[f] for f,Fval in enumerate(F)] )
=======
    def output(self,F,inputVar=None): return sumVars( elementwiseMultiply(F,self.bpOutputs) )
>>>>>>> added linear bid model. much cleaner formulation.
=======
    def output(self,variables,iden): 
        F = [variables['{iden}_f{bpNum}'.format(bpNum=f,iden=iden)] for f in range(len(self.bpInputs))]
<<<<<<< HEAD
        return sumVars( elementwiseMultiply(F,self.bpOutputs) )
<<<<<<< HEAD
>>>>>>> cleaner handling of different bid models. fix for the convex bid model, due to confusion from ugly code.
    def trueOutput(self,input): return polyval( self.polyCurve,         value(input) )
    def incOutput(self,input):  return polyval( polyder(self.polyCurve),value(input) )
=======
    def trueOutput(self,inputVar): return polyval( self.polyCurve,         value(inputVar) )
    def incOutput(self,inputVar):  return polyval( polyder(self.polyCurve),value(inputVar) )
>>>>>>> added user breakpoint control by moving buildCostModel into add_timevars
=======
        return sum_vars( elementwiseMultiply(F,self.bpOutputs) )
    def output_true(self,inputVar): return polyval( self.polyCurve,         value(inputVar) )
    def output_incremental(self,inputVar):  return polyval( polyder(self.polyCurve),value(inputVar) )
>>>>>>> refactored powersystems. moving on to bidding
=======
    def output(self,variables,input_var,status_var,owner_iden,time_iden): 
        F = [variables[self._f_name(f,owner_iden,time_iden)] for f in range(len(self.bpInputs))]
        return sum_vars( elementwiseMultiply(F,self.bpOutputs) )
    def output_true(self,input_var): return polyval( self.polyCurve, value(input_var) )
    def output_incremental(self,input_var):  return polyval( polyder(self.polyCurve),value(input_var) )
>>>>>>> first draft of refactor
=======
    def output(self,variables,owner_iden,time_iden): 
        F = [variables[self._f_name(f,owner_iden,time_iden)] for f in range(len(self.bp_inputs))]
<<<<<<< HEAD
        return sum_vars( elementwiseMultiply(F,self.bp_outputs) )
<<<<<<< HEAD
    def output_true(self,input_val): return polyval( self.poly_curve, value(input_val) )
    def output_incremental(self,input_var):  return polyval( polyder(self.poly_curve),value(input_var) )
>>>>>>> redo of bid, bid.model input and status variable handling
=======
=======
=======
    def output(self,variables,owner_iden,time_iden,evaluate=False): 
        F = [variables[self._f_name(f,owner_iden,time_iden)] for f in range(len(self.bp_inputs))]
=======
    def output(self,bid,owner_iden,time_iden,evaluate=False): 
        F = [bid.get_variable(self._f_name(f,owner_iden,time_iden)) for f in range(len(self.bp_inputs))]
>>>>>>> clean up variables in bids
=======
    def output(self,bid,evaluate=False): 
        F = [bid.get_variable(self._f_name(f,bid.owner_iden,bid.time_iden)) for f in range(len(self.bp_inputs))]
>>>>>>> update docs
        if evaluate: F=map(value,F)
>>>>>>> add evaluate option to costs (coopr sums). add storage of generation power and status for UC results
        return sum( elementwiseMultiply(F,self.bp_outputs) )
>>>>>>> merged in changes from DR_model
    def output_true(self,input_val): return float(polyval( self.poly_curve, value(input_val) ))
    def output_incremental(self,input_var):  return float(polyval( polyder(self.poly_curve),value(input_var) ))
>>>>>>> float the numpy output_true
    def texrepresentation(self,digits=3):
        '''
        Output polynomial to tex-style string.
        
        >>> texrepresentation([ 7,  6, -5])
        '-5+6P+7P^2'    
        '''        
        texstr=''
        exp=0
        for n in reversed(self.poly_curve.c):
            if round(n,digits)==0 and exp!=0: continue
            addChar='+' if n>0 else ''
            if exp>1: texstr+='{pm}{n:0.{d}f}P^{exp}'.format(pm=addChar,n=n,exp=exp,d=digits)
            elif exp==1: texstr+='{pm}{n:0.{d}f}P'.format(pm=addChar,n=n,d=digits)
            elif exp==0: texstr+='{pm}{n:0.{d}f}'.format(pm=addChar,n=n,d=digits)
            exp+=1
        if texstr[0]=='+': texstr=texstr[1:]
        return texstr
=======
def polynomial_incremental_value(multipliers,variable):
    """get the incremental value of a polynomial"""
    return sum([(mult*order*variable**(order-1) if order>0 else 0) for order,mult in enumerate(multipliers)])
>>>>>>> use native pyomo.Piecewise to do bidding linearization models

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
    
<<<<<<< HEAD
<<<<<<< HEAD
    x=((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
    y=((x1*y2-y1*x2)*(y3-y4)-(y1-y1)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
    return (x,y)
def get_slope(line):
    '''Get the intersection a line function'''
    x1,x2=0,1
    y1,y2=line(x1),line(x2)
    m=(y2-y1)/(x2-x1)
    return m
=======
    return multipliers
>>>>>>> use native pyomo.Piecewise to do bidding linearization models
=======
    return multipliers

def get_line_slope(A,B):
    xA,yA = A
    xB,yB = B
    return (yB-yA)*1.0/(xB-xA)
def get_line_value(A,B,x):
    # take a pair of points and make a linear function
    # get the value of the function at x
    # see http://bit.ly/Pd4z4l
    xA,yA = A
    slope = get_line_slope(A,B)
    return slope*(value(x) - xA) + yA
<<<<<<< HEAD
>>>>>>> custom specification of pwl bid points
=======
>>>>>>> add no load cost for custom bid points
