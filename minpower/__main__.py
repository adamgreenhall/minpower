"""
Call the minpower package as a command:
    python minpower ./myproblemdir
"""

import sys,os
from solve import main

if __name__ == '__main__':
    ''' command line input'''
    if len(sys.argv)==1: main()
    elif len(sys.argv)==2: 
        datadir=sys.argv[1]
        if not os.path.isdir(datadir):
            raise OSError( "data directory does not exist: '{d}'".format(d=datadir) )
        main(datadir=datadir)
    else: 
        raise IOError('solve.main() takes only one input argument (the directory). {n} inputs passed'.format(n=len(sys.argv)))

