import sys
import clint
import subprocess
import os
from ipdb import set_trace

def main():
    scheduler_args = ['qsub',
        '-l nodes=1:ppn=12,feature=12core,mem=16gb,walltime=10:00:00',
        '-m ae', #mail on completion/failure
        '-M argreen@uw.edu'
        ] 

    minpower_args = ['minpower']+clint.args.all

    if not '-p' in minpower_args: 
        # subprocess style
        minpower_args.append('-p')

    print minpower_args

    # 
    if 'hyak' not in os.uname()[1]:
        scheduler_args = []

    pid = subprocess.Popen( scheduler_args+minpower_args, 
        stdout=sys.stdout,
        stderr=subprocess.STDOUT,
        ).pid

    print 'opening {}'.format(pid)
        
    print 'done'
    
if __name__=='__main__': main()
