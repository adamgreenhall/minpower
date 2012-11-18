import sys
import clint
import subprocess
import os
from ipdb import set_trace

def main():

    minpower_args = [' minpower']+clint.args.all

    if not '-p' in minpower_args:
        # subprocess style
        minpower_args.append('-p')

    print minpower_args

    if 'hyak' not in os.uname()[1]:
        scheduler_args = []
    else:
        scheduler_args = ['qsub',
            '-l nodes=1:ppn=12,feature=12core,mem=16gb,walltime=10:00:00',
            '-m ae', #mail on completion/failure
            '-M argreen@uw.edu'
            ]
        # see https://sig.washington.edu/itsigs/Hyak_Job_Scheduler
        
        # check that paths are absolute
        case_dir = os.path.dirname(clint.args.files[0])
        if case_dir != os.path.abspath(case_dir):
            raise IOError('paths have to be absolute for hyak')
        
        # there should be a better way than having to call a script on disk
        script_name = './call{}.sh'.format(os.getpid())
        with open(script_name, 'w+') as f:
            f.write(' '.join(minpower_args))
        minopwer_args = [script_name]

    pid = subprocess.Popen( scheduler_args+minopwer_args,
        stdout=sys.stdout,
        stderr=subprocess.STDOUT,
        ).pid

    print 'opening {}'.format(pid)

    print 'done'

if __name__=='__main__': main()

