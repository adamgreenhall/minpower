import sys
import clint
import subprocess
import os

def main():
    '''
    a wrapper to make the minpower script work with cluster schedulers
    or with an ssh call that you start on your laptop and then close the
    connection.
    '''
    minpower_args = ['minpower']+clint.args.all

    # subprocess style
    if not '-p' in minpower_args:
        minpower_args.append('-p')
    if not '--standalone' in minpower_args:
        minpower_args.append('--standalone')

    print minpower_args

    if 'hyak' not in os.uname()[1]:
        scheduler_args = ['nohup']
        stdout = open('{}.out'.format(os.getpid()),'w')
        stderr = open('{}.err'.format(os.getpid()),'w')
    else:
        scheduler_args = ['qsub',
            '-l nodes=1:ppn=12,feature=12core,mem=16gb,walltime=48:00:00',
            '-m ae', #mail on completion/failure
            '-M argreen@uw.edu'
            ]
        # see https://sig.washington.edu/itsigs/Hyak_Job_Scheduler
        # default walltime limit is only one hour - must set this

        # these get redirected by hyak anyway
        stdout = sys.stdout
        stderr = subprocess.STDOUT

        # check that paths are absolute
        case_dir = os.path.dirname(clint.args.files[0])
        if case_dir != os.path.abspath(case_dir):
            raise IOError('paths have to be absolute for hyak')

        # there should be a better way than having to call a script on disk
        script_name = './call{}.sh'.format(os.getpid())
        with open(script_name, 'w+') as f:
            f.write(' '.join(minpower_args))
        minpower_args = [script_name]

    pid = subprocess.Popen( scheduler_args + minpower_args,
        stdout=stdout,
        stderr=stderr,
        ).pid

    print 'parent process {}'.format(os.getpid())
    print 'starting run {}'.format(pid)


if __name__=='__main__': main()

