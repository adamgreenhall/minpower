""" 
Testing for minpower development. 
Runs solve.problem() on all directory named in inputs.
"""
import os

from minpower import solve,config
from minpower.commonscripts import joindir,splitFilename

def problem(test_name='uc'):
    test_dir=splitFilename(__file__)[0]
    dir=joindir(test_dir,test_name)
    if os.path.isdir(dir): solve.problem(dir)
    else:
        msg='"{}" is not a minpower test case.'.format(test_name) 
        raise OSError(msg)