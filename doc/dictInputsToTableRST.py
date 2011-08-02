import os, operator
from minpower import get_data
def tableFromD(D,className=None):
	classPrepend=':py:attr:`~'
	classMid='.'
	classAppend='`'
	L= sorted(D.iteritems(), key=operator.itemgetter(0))
	L.insert(0,('Field','Attribute'))
	fLen,aLen=[],[]
	for f,a in L: 
		fLen.append(len(f))
		aLen.append(len(a))
	n,m=max(fLen),max(aLen)
	n+=5
	m+=5
	if className is not None: n+=len(classPrepend+className+classMid+classAppend)
	print '='*m,'  ','='*n
	for i,(f,a) in enumerate(L):
		if className is None or i==0: print f,' '*(m-len(f)),' ',a
		else: print f,' '*(m-len(f)),' ',classPrepend+className+classMid+a+classAppend
		if i==0: 	print '='*m,'  ','='*n		
	print '='*m,'  ','='*n
	print 
	
tableFromD(get_data.fields_gens,className='powersystems.Generator')
tableFromD(get_data.fields_lines,className='powersystems.Line')
tableFromD(get_data.fields_loads,className='powersystems.Load')

