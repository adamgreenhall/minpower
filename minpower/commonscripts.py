"""
Short, commonly used scripts. 
Many of them are one liners.
"""

import os
import csv
import itertools,operator
import datetime
from dateutil import parser

try: # for development
    from pdb import set_trace as debug #pudb
except: pass 

def bool_to_int(x): return 1 if x else 0

###### matrix stuff #######
def getColumn(matrix,colNum): return [row[colNum] for row in matrix]#equiv to matrix(:,j)
def elementwiseMultiply(La,Lb): return map(operator.mul, La,Lb)
def elementwiseAdd(La,Lb): return map(operator.add, La,Lb)
def transpose(listoflists): return map(None,*listoflists)
def flatten(listoflists):
    '''Flatten one level of nesting'''
    return list(itertools.chain.from_iterable(listoflists))
def unflatten(flatlist,levels):
    '''Turn a flat list into a nested list, with a specified number of lists per nesting level.
    Excess elements are silently ignored.
        
    >>> unflatten(range(12),[2,2,3])
    [[[0, 1, 2], [3, 4, 5]], [[6, 7, 8], [9, 10, 11]]]
    '''
    def nestgenerator(flatlist,levels):
        if levels:
            it = nestgenerator(flatlist,levels[1:])
            while 1: yield list(itertools.islice(it,levels[0]))
        else:
            for d in flatlist: yield d        
    return nestgenerator(flatlist,levels).next()
def unique(seq): 
    # order preserving, <http://bit.ly/pyUnique>
    U = []
    [U.append(i) for i in seq if not U.count(i)]
    return U
def within(x, val=0, eps=1e-3): return (val-eps) <= x <= (val+eps)

def frange(start, stop, step=1.0):
    """Like range(), but returns list of floats instead
    All numbers are generated on-demand using generators
    """

    cur = float(start)
    while cur < stop:
        yield cur
        cur += step

def replace_all(seq, obj, replacement):
    def with_index(seq):
        for i in xrange(len(seq)): yield i, seq[i]

    for i, elem in with_index(seq):
        if elem == obj: seq[i] = replacement
    return seq
    
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.izip(a, b)

##### csv stuff #####
def csvColumn(filenm,fieldNm):
    '''get a single column of csv data'''
    data,fields=readCSV(filenm)
    try: num=fields.index(fieldNm) #column number to return
    except ValueError or IndexError: num=indexCaseSpaceInsensitive(fields,fieldNm) #try again with case and space insensitive        
    return getColumn(data,num)

def readCSV(filenm,validFields='all'):
    """
    Read data from a csv into a list of lists. 
    Does parsing of each cell with :func:`csvDataConvert`.
    Field order doesn't matter. If validFields is not 'all' and
    a field is not in validFields, its data will be excluded from 
    the output data.
        
    :param filenm: name of the csv file to read
    :param validFields: list of valid field names (case and space insensitive)
    
    :returns: data, a list of lists
    :returns: fieldsChecked, a list of fields 
    """
    csvfile = open(filenm)
    try: dialect = csv.Sniffer().sniff(csvfile.read(4048))
    except: 
        #this generally happens when the file is very short
        #assume dialect is excel
        dialect = csv.excel
    csvfile.seek(0)
    reader = csv.reader(csvfile, dialect)
    def csvDataConvert(inData, repForBlankStrings=None, checkForNumbers=True):
        outData=[]
        for row in inData:
            newRow=[]
            for entry in row:
                entry=entry.strip()
                if entry.strip()=='': newRow.append( repForBlankStrings )
                elif checkForNumbers: newRow.append( convert_str2num(entry) )
                else: newRow.append(entry)
            #if not all(e=='' for e in newRow): 
            outData.append(newRow)
        return outData
    
    data=csvDataConvert(zip(*reader))
    csvfile.close()
    
    try: data=transpose(data) #return data in r,c index order 
    except TypeError:
        print 'data for {file} is length: {n}'.format(file=filenm,n=len(data))
        print 'file is {n}B'.format(n=os.path.getsize(filenm))
        raise
    fields=data.pop(0) #fields are the first row of csv
    
    if validFields=='all': return data,fields
    else: #ensure that each field is in validFields
        
        fieldsChecked=list(fields[:])
        for i,field in enumerate(fields): 
            if field in validFields: continue
            else: 
                fieldSimple=drop_case_spaces(field)
                if fieldSimple in validFields: fieldsChecked[fieldsChecked.index(field)]=fieldSimple #compare without considering case or spaces
                elif fieldSimple is not None: print 'Ignored "{f}" as not a valid input field for {nm}. '.format(f=field,nm=filenm)
        
        return data,fieldsChecked    

def csv2dicts(filename,field_map=None):
    def valid_cell(name,val): return name is not None and val.strip()!='' 
    with open(filename,'r') as csvfile:
        try: dialect = csv.Sniffer().sniff(csvfile.read(4048))
        except: dialect = csv.excel
        csvfile.seek(0)
        raw_data=list(csv.DictReader(csvfile, dialect=dialect))
    if field_map is not None: 
        try: data=[{field_map[drop_case_spaces(name)]:convert_str2num(val) for name,val in row.items() if valid_cell(name,val)} for row in raw_data]
        except: 
            print raw_data
            raise
    else:
        data=[{name:convert_str2num(val) for name,val in row.items() if valid_cell(name,val)} for row in raw_data]
    return data 

def writeCSV(fields,data,filename):
    with open(filename, 'w+') as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        writer.writerows(data)
        
#################### string stuff ##################
def convert_str2num(s):
    s=s.strip()
    try: return int(s)
    except ValueError: 
        try: return float(s)
        except ValueError: return s
def indexCaseSpaceInsensitive(L,s): return map(drop_case_spaces,L).index( drop_case_spaces(s) )
def drop_case_spaces(s): 
    '''get rid of spaces in a string and make lower case. will also work with list of strings'''
    try: return s.lower().replace(' ','')
    except AttributeError: 
        if s is None: return None
        elif isinstance(s, list): return map(drop_case_spaces,s)

def toPercent(val,digits=0): return '{p:.{d}%}'.format(p=val,d=digits)            
##################### file stuff ###########################
def splitFilename(fullPathFilenm):
    '''split a filename into its directory, filename, and extension'''
    (dirNm,fullFilenm)=os.path.split(fullPathFilenm)
    (fileNm,extNm)=os.path.splitext(fullFilenm)
    return dirNm, fileNm, extNm
def joindir(dir,file): return os.path.join(dir, file)
            
################### time stuff ###########################
def parseTime(str,formatter=None): 
    if formatter is None: return parser.parse(str)
    else: return parser.parse(str,**formatter)
def getTimeFormat(str):
    formatter=dict()
    t=parseTime(str)
    if t == parseTime(str,dict(dayfirst=True)): formatter['dayfirst']=True
    if t == parseTime(str,dict(yearfirst=True)): formatter['yearfirst']=True
    return formatter
def hours(t): 
    try:  return t.days*24.0 + t.seconds/3600.0 #t is a datetime object
    except AttributeError: return datetime.timedelta(hours=t) #t is a number
def show_clock(show=True):
    return 'clock time={}'.format(datetime.datetime.now().strftime('%H:%M:%S')) if show else ''

####################### class stuff #######################
def getattrL(L,attribute='name'):
    '''get the attribute of each class instance in a list'''
    return [getattr(item,attribute) for item in L]
def getclass_inlist(L,values,attribute='name'):
    if isinstance(values,str): values=[values]
    attrL=getattrL(L,attribute)
    try: indL=[attrL.index(value) for value in values]
    except ValueError:
        print attrL
        raise
    if len(indL)==1: return L[indL[0]]
    else: return [L[ind] for ind in indL]

def update_attributes(instance, variables, exclude=['self'],include=None):
    """Update instance attributes
 
    For example, update(self, locals())
    
    instance: Instance to update via setattr()
    variables: Dictionary of variables
    exclude: Variables to explicitly exclude, defaults to ['self'].
    include: Variables to explicitly include. If set, include overides exclude.
    """
    if include is not None: [setattr(instance,k,v) for k,v in variables.items() if k in include]
    else:
        if 'self' not in exclude: exclude.append('self')
        [setattr(instance, k, v) for k, v in variables.items() if k not in exclude]
 
####################### dict stuff ########################
def subset(D, subsetL):
    '''subset of dictionary'''
    subsetLcopy=subsetL
    for k,key in enumerate(subsetL): #ensure that subset doesn't contain any keys not in D already
        if key not in D: subsetLcopy.pop(k)
    return dict(zip(subsetL, map(D.get, subsetLcopy)))
def subsetexcept(D,exceptL):
    '''dictionary without exceptions list'''
    for e in exceptL: D.pop(e)
    return D


def show_memory_backrefs(name):
    import objgraph
    objgraph.show_backrefs(objgraph.by_type(name),filename='backrefs-{}.png'.format(name))
def show_memory_refs(name):
    import objgraph,inspect
    try: obj=objgraph.by_type(name)[0]
    except IndexError:
        print 'no object of type',name  
        return
    objgraph.show_chain(objgraph.find_backref_chain( obj , inspect.ismodule),filename='chain-{}.png'.format(name))
def show_memory_growth():
    import objgraph
    objgraph.show_growth()
