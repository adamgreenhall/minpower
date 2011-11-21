from commonscripts import elementwiseMultiply,update_attributes
from optimization import value,new_variable,sum_vars,OptimizationObject
from config import default_num_breakpoints

from scipy import linspace, polyval, polyder, interp, poly1d

#import matplotlib
#from sys import platform as osname
#if osname=='darwin': matplotlib.use('macosx') #avoid popups when using matploblib to savefig on MacOSX
from pylab import plot,savefig,xlabel,ylabel

import re

class Bid(OptimizationObject):
    """
    Descibes a bid as modeled by :attr:model. Bids contain variables
    which are dependent on time while :class:`~bidding.PWLmodel` objects
    do not store time dependent information.
    
    :param model: model for the bid, either :class:`~bidding.PWLmodel`,
        :class:`~bidding.convexPWLmodel`, or :class:`~bidding.LinearModel`  
    :param time: :class:`~schedule.Time` object bid takes place over 
    :param owner_iden: identifying string for the bidder
    :param time_iden: identifying string for the time
    :param input_var: input variable for owner at time period of bid
    :param status_var: status of owner at time period of bid
    """
    def __init__(self,model,time,owner_iden,time_iden,input_var=0,status_var=True):
        update_attributes(self,locals(),exclude=['input_var','status_var'])
        self.init_optimization()
        self.variables['input'] = input_var
        self.variables['status']= status_var 
    def output_true(self,input_val): 
        '''true output value of bid'''
        return self.model.output_true(input_val)
    def output_incremental(self,input_val):
        '''incremental output value of bid'''
        return self.model.output_incremental(input_val)
    def plot_derivative(self,**kwargs): return self.model.plot_derivative(**kwargs)
    def plot(self,P=None,filename=None,showPW=False):
        plotted=self.model.plot(P,showPW=showPW)
        if filename is not None: savefig(filename)
        return plotted
    
    def create_variables(self):
        '''Call the :attr:model and get any additional variables from it.'''
        self.variables.update(self.model.get_time_variables(self.variables['input'],
                                                            self.variables['status'],
                                                            self.owner_iden,self.time_iden))
    def create_constraints(self):
        '''
        Create the constraints for a bid by calling its model's :meth:`get_time_constraint` method.
        :return: a dictionary of the bid's constraints 
        '''
        constraintD=self.model.get_time_constraints(self.variables,self.owner_iden,self.time_iden)
        for nm,expr in constraintD.items(): self.add_constraint(nm,self.time,expr)
        return self.constraints
    def output(self): 
        '''The output of the bid, given an input.'''
        return self.model.output(self.variables,self.owner_iden,self.time_iden)   
    def __str__(self): return 'bid{t}'.format(t=str(self.time))
    def iden(self,*args): return 'bid{t}'.format(t=str(self.time))


def makeModel(polyText,multiplier=1, **kwargs):
    '''Create a model for a polynomial. Decide which model to use based on the polynomial.'''
    polyCurve=multiplier * parsePolynomial(polyText)
    if isLinear(polyCurve):
        return LinearModel(polyText,multiplier,**kwargs)
    elif isConvex(polyCurve):
        return convexPWLmodel(polyText,multiplier,**kwargs)
    else:
        return PWLmodel(polyText,multiplier,**kwargs)
    
        
    
class PWLmodel(object):
    """
    A piecewise linear model of a polynomial.
    
    :param polyText: a string defining the polynomial 
      (see :meth:`~bidding.parsePolynomial` for more on parsing)
    :param multiplier: an optional  multiplier (default is 1) for
      the whole polynomial (used for converting heat rate
      curves to cost curves)
    :param num_breakpoints: number of breakpoints to use when linearizing
      the polynomial (currently the default comes from :mod:`config`)
    :param (min/max)Input: domain of polynomial to consider
    :param (input/output)Nm: names of in/outputs (for plotting)
    """
    def __init__(self,
        polyText='2+10P+0.1P^2',multiplier=1,
        min_input=0,max_input=10000,
        num_breakpoints=default_num_breakpoints,
        input_name='x',output_name='y'):
                
        update_attributes(self,locals(),exclude=['polyText','multiplier'])
        self.poly_curve=multiplier * parsePolynomial(polyText) #parse curve
    def do_segmentation(self):
        '''Create the segmentation of the polynomial with num_breakpoints-1 segments.'''
        if isLinear(self.poly_curve): self.num_breakpoints=2 #linear models only need 2 breakpoints
        inDiscrete=linspace(self.min_input, self.max_input, 1e6) #fine discretization of the curve
        outDiscrete=polyval(self.poly_curve,inDiscrete)
        self.bp_inputs = [float(bpi) for bpi in linspace(self.min_input, self.max_input, self.num_breakpoints)] #interpolation to get pwl breakpoints
        self.bp_outputs= [float(bpo) for bpo in interp(self.bp_inputs,inDiscrete,outDiscrete)]
        self.segments=range(1,len(self.bp_inputs))
        
    def plot(self,P=None,linestyle='-',showPW=True,color=None):
        inDiscrete=linspace(self.min_input, self.max_input, 1e6)
        outDiscrete=polyval(self.poly_curve,inDiscrete)
        if showPW:
            try: plot(self.bp_inputs,self.bp_outputs,linestyle='.--') #show piecewise linearization
            except AttributeError: pass                             #this is a linear model - dont need to show the linearization
        linePlotted, = plot(inDiscrete,outDiscrete,linestyle=linestyle) #show continuous curve
        
        xlabel(self.inputNm)
        ylabel(self.outputNm)
        if P is not None: plot(P,polyval(self.poly_curve,P), 'o', c=linePlotted.get_color(), markersize=8, linewidth=2, alpha=0.7) 
        return linePlotted
    def plot_derivative(self,P=None,linestyle='-',color=None):
        deriv=polyder(self.poly_curve)
        inDiscrete=linspace(self.min_input, self.max_input, 1e6)
        outDiscrete=polyval(deriv,inDiscrete)
        if color is None: 
            linePlotted, = plot(inDiscrete,outDiscrete,linestyle=linestyle)          #show continuous curve
        else: 
            linePlotted, = plot(inDiscrete,outDiscrete,linestyle=linestyle,color=color)
        
        if P is not None: plot(P,polyval(deriv,P), 'o', c=linePlotted.get_color(), markersize=8, linewidth=2, alpha=0.7)
        return linePlotted            
    def _f_name(self,bpNum,owner_iden,time_iden):  return '{oi}_f{bpNum}_{ti}'.format(bpNum=bpNum,oi=owner_iden,ti=time_iden)
    def _s_name(self,segNum,owner_iden,time_iden): return '{oi}_s{segNum}_{ti}'.format(segNum=segNum,oi=owner_iden,ti=time_iden)
    def get_time_variables(self,input_var,status_var,owner_iden,time_iden):
        variables={}
        self.do_segmentation()
        #S: segment of cost curve is active
        #F: breakpoint weighting fraction
        for segNum in range(len(self.segments)):
            name=self._s_name(segNum,owner_iden,time_iden)
            variables[name] = new_variable(kind='Binary', name=name)
         
        for bpNum in range(len(self.bp_inputs)):
            name=self._f_name(bpNum,owner_iden,time_iden)
            variables[name] = new_variable(low=0,high=1,  name=name)
        return variables 
    def get_time_constraints(self,variables,owner_iden,time_iden):
        """
        Create the constraints for a single time instance of 
          a piecewise linear model. 
          
        :param variables: a dictionary of the variables for the bid
        :param iden: identifying string for the bidder and time interval
        
        :returns: a dictionary of constraints
        """
        constraints=dict()
        iden=owner_iden+time_iden
        input_var=variables['input']
        status_var=variables['status']
        if status_var in (True,False): status_var=1 if status_var else 0 #convert bool to integer for coopr 
        
        S = [variables[self._s_name(s,owner_iden,time_iden)] for s in range(len(self.segments))] 
        F = [variables[self._f_name(f,owner_iden,time_iden)] for f in range(len(self.bp_inputs))]

        constraints['oneActiveSegment '+iden]= sum_vars(S)== status_var 
        constraints['fractionSums '+iden]    = sum_vars(F) == status_var 
        constraints['computeInput '+iden]    = input_var == sum_vars( elementwiseMultiply(F,self.bp_inputs) )
        constraints['firstSegment '+iden]    = F[0]<=S[0]
        constraints['lastSegment '+iden]     = F[-1]<=S[-1]
        for b in range(1,self.num_breakpoints-1): 
            name='midSegment {iden} b{bnum}'.format(iden=iden,bnum=b)
            constraints[name]                = ( F[b] <= sum_vars([S[b-1],S[b]]) )
        return constraints
    def output(self,variables,owner_iden,time_iden): 
        F = [variables[self._f_name(f,owner_iden,time_iden)] for f in range(len(self.bp_inputs))]
        return sum_vars( elementwiseMultiply(F,self.bp_outputs) )
    def output_true(self,input_val): return float(polyval( self.poly_curve, value(input_val) ))
    def output_incremental(self,input_var):  return float(polyval( polyder(self.poly_curve),value(input_var) ))
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


class convexPWLmodel(PWLmodel):
    '''
    A piecewise linear model for a monotonically increasing polynomial.
    This formulation results in no additional binary variables (in constrast to the more 
    general :class:`~bidding.PWLmodel`). A objective minimization problem is assumed.
    '''
    def __init__(self,
        polyText='2+10P+0.1P^2',multiplier=1,
        min_input=0,max_input=10000,
        num_breakpoints=default_num_breakpoints,
        input_name='x',output_name='y'):
        
        update_attributes(self,locals(),exclude=['polyText','multiplier'])
        self.poly_curve=multiplier * parsePolynomial(polyText) #parse curve
    def do_segmentation(self):
        def linear_equation(x,m,b): return m*x+b
        def make_lineareq(x1,y1,x2,y2):
            m=(y2-y1)/(x2-x1)
            b=y1-x1*m
            return lambda x: linear_equation(x,m,b)
        
        inDiscrete=linspace(self.min_input, self.max_input, 1e6) #fine discretization of the curve
        outDiscrete=polyval(self.poly_curve,inDiscrete)
        self.bp_inputs = [float(bpi) for bpi in linspace(self.min_input, self.max_input, self.num_breakpoints)] #interpolation to get pwl breakpoints
        self.bp_outputs= [float(bpo) for bpo in interp(self.bp_inputs,inDiscrete,outDiscrete)]
        self.segment_lines=[]
        for b,x1 in enumerate(self.bp_inputs[:-1]):
            x2,y2=self.bp_inputs[b+1],self.bp_outputs[b+1]
            y1=self.bp_outputs[b]
            self.segment_lines.append(make_lineareq(x1,y1,x2,y2))
    
    def output_true(self,input_val): return float(polyval( self.poly_curve, value(input_val) ))
    def output_incremental(self,input_val):  return float(polyval( polyder(self.poly_curve),value(input_val) ))
    def plot(self,P=None,showPW=True,linestyle='-',color='k'):
        inDiscrete=linspace(self.min_input, self.max_input, 1e6)
        outDiscrete=polyval(self.poly_curve,inDiscrete)
        plot(inDiscrete,outDiscrete,linestyle=linestyle,alpha=0.5,color='gray')          #show continuous curve
               
        if showPW: 
            x=linspace(self.min_input, self.max_input, 1e6)
            for line in self.segment_lines: linePlotted, = plot(x,line(x),linestyle='--',alpha=0.4,color=color) #show piecewise linearization
        xlabel(self.inputNm)
        ylabel(self.outputNm)
        if P is not None: plot(P,polyval(self.poly_curve,P), 'o', c=linePlotted.get_color(), markersize=8, linewidth=2, alpha=0.7) 
        return linePlotted
    def plot_derivative(self,P=None,linestyle='-',color=None):
        power,IC=[],[]
        x_low=self.min_input
        x_high=x_low
        for i,line in enumerate(self.segment_lines):
            x_low=x_high
            try: 
                next_line=self.segment_lines[i+1]
                x_high=find_intersection(line,next_line)[0]
            except IndexError: 
                x_high=self.max_input
            power.append(x_low)
            IC.append(get_slope(line))
        else:
            power.append(x_high)
            IC.append(get_slope(line))
        
        linePlotted,=plot(power,IC,drawstyle='steps-post')
         
        if P is not None: plot(P,polyval(polyder(self.poly_curve),P), 'o', c=linePlotted.get_color(), markersize=8, linewidth=2, alpha=0.7)
        return linePlotted
    def get_time_variables(self,input_var,status_var,owner_iden,time_iden):
        variables={}
        name = 'bidCost_'+owner_iden+time_iden
        variables[name] = new_variable(name=name,high=float(max(self.bp_outputs)))
        return variables
    def get_time_constraints(self,variables,owner_iden,time_iden):
        constraints=dict()
        for b,line in enumerate(self.segment_lines): 
            nm='cost_linearized_{oi}_b{b}_{ti}'.format(oi=owner_iden,b=b,ti=time_iden)
            constraints[nm]= variables['bidCost_'+owner_iden+time_iden] >= line(variables['input'])
        return constraints
    def output(self,variables,iden_owner,iden_time): return variables['bidCost_'+iden_owner+iden_time]
class LinearModel(PWLmodel):
    '''
    A simple linear model for a linear polynomial.
    This class exists to keep the calling conventions the same 
    as those in :class:`~bidding.PWLmodel`.
    '''    
    def __init__(self,
        polyText='2+10*P',multiplier=1,
        min_input=0,max_input=10000,
        num_breakpoints=None,
        input_name='x',output_name='y'):
        update_attributes(self,locals(),exclude=['polyText','multiplier'])
        self.poly_curve = multiplier * parsePolynomial(polyText)

    def get_time_variables(self,*args,**kwargs): return {}
    def get_time_constraints(self,*args,**kwargs): return {}
    def output(self,variables,owner_iden,time_iden):
        try: fixed_term=self.poly_curve.c[1]*variables['status']
        except IndexError: fixed_term=0 #constant cost
        linear_term = self.poly_curve.c[0]*variables['input']
        return fixed_term + linear_term
    
    
def isLinear(P):
    """Check if a polynomial object is linear using its order attribute."""
    return True if P.order<=1 else False 
def isConvex(P):
    #convexity is complicated: http://plus.maths.org/content/convexity
    #so for now: if all polynomial coefs are positive, call it convex
    return True if all(coef>=0 for coef in P.c) else False
    
def parsePolynomial(s):
    """
    Parse a string into a numpy polynomial object.
    Heavily adapted from `<http://bit.ly/polynomialParse>`_.
    
    Can handle simple polynomials (addition and subtraction):     
    
    >>> parsePolynomial('7x^2 + 6x - 5')
    poly1d([ 7,  6, -5])
    
    or with the explicit * multiplier:
    
    >>> parsePolynomial('7*P^2 + 6*P - 5')
    poly1d([ 7,  6, -5])
    
    or even with the terms in some random order: 
    
    >>> parsePolynomial('6*P - 5 + 7*P^2')
    poly1d([ 7,  6, -5])
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
        res = powerPattern.findall(s)[0]
        if not res: return 1
        return int(res)
    s=str(s).replace(' ','') #remove all whitespace from string
    m = re.search('[a-zA-Z]+', s) 
    try: varLetter=m.group(0)
    except AttributeError: varLetter='P'
    termPattern = re.compile('([+-]?\d*\.?\d*)\**({var}?\^?\d?)'.format(var=varLetter))
    powerPattern = re.compile('{var}\^?(\d)?'.format(var=varLetter))
    res_dict = {}
    
    for n,p in termPattern.findall(s):
        n,p = n.strip(),p.strip()
        if not n and not p: continue
        n,p = parse_n(n),parse_p(p,powerPattern)
        if res_dict.has_key(p): res_dict[p] += n
        else: res_dict[p] = n
    highest_order = max(res_dict.keys())
    res = [0]*(highest_order+1)
    for key,value in res_dict.items(): res[key] = value
    res.reverse() #reverse the order of the polynomial
    return poly1d(res,variable=varLetter)

def find_intersection(A,B):
    '''Get the intersection point of two line functions'''
    #http://en.wikipedia.org/wiki/Line-line_intersection
    x1,x2=0,5
    x3,x4=0,5
    y1,y2=A(x1),A(x2)
    y3,y4=B(x3),B(x4)
    
    x=((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
    y=((x1*y2-y1*x2)*(y3-y4)-(y1-y1)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
    return (x,y)
def get_slope(line):
    '''Get the intersection a line function'''
    x1,x2=0,1
    y1,y2=line(x1),line(x2)
    m=(y2-y1)/(x2-x1)
    return m