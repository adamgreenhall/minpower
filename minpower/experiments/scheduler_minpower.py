import sys
import argparse
import subprocess
import os
from pprint import pprint
from minpower.config import (parse_command_line_config,
                             scheduler_config, user_config)


def main():
    '''
    a wrapper to make the minpower script work with cluster schedulers
    or with an ssh call that you start on your laptop and then close the
    connection.
    '''

    default_minpower_config = dict(user_config).copy()
    parser = argparse.ArgumentParser(
        description='Minpower scheduler command line interface')

    parser.add_argument('--scheduler_mode',
                        default=scheduler_config.scheduler_mode,
                        choices=['qsub', 'nohup', 'pass'],
                        help='''Mode of scheduler operation:
        qsub: use the qsub cluster scheduler
        nohup: use nohup, call as subprocess, and redirect stdin, stderr
        pass: just call minpower as a child process (for debugging)
        ''')
    parser.add_argument('--verbose', action="store_true",
                        default=scheduler_config.verbose)
    parser.add_argument('--dry_run', action="store_true",
                        help="just show, don't do", default=False)

    qsub_opts = parser.add_argument_group('qsub options',
                                          description='the following options only apply if using qsub')
    qsub_opts.add_argument('--email',
                           default=scheduler_config.email,
                           help='email on scheduler job completion')
    qsub_opts.add_argument('--memory',
                           type=int, default=scheduler_config.memory,
                           help='gigabytes of memory to limit job to')
    qsub_opts.add_argument('--hours_limit',
                           type=int, default=scheduler_config.hours_limit,
                           help='hours of runtime to limit job to')

    args, minpower_args_raw = parser.parse_known_args()

    minpower_parser = argparse.ArgumentParser('minpower')
    minpower_args = parse_command_line_config(minpower_parser,
                                              preparsed_args=minpower_args_raw)

    # scheduler config can be loaded from the case directory
    parser.set_defaults(**dict(scheduler_config))
    args, __ = parser.parse_known_args()

    # subprocess style
    minpower_args['standalone'] = True
    minpower_args['pid'] = minpower_args['pid'] \
        if minpower_args['pid'] else os.getpid()

    if args.scheduler_mode == 'qsub':
        # qsub makes all of its script calls from the home directory
        # so it requires an absolute path
        minpower_args['directory'] = os.path.abspath(
            minpower_args['directory'])

        if 'scenarios_directory' in minpower_args and minpower_args['scenarios_directory']:
            minpower_args['scenarios_directory'] = os.path.abspath(
                minpower_args['scenarios_directory'])

    if args.verbose:
        pprint(minpower_args)

    scheduler_call = []
    minpower_call = ['minpower']
    stdout = sys.stdout
    stderr = subprocess.STDOUT

    def arg2str(k, v):
        if k == 'directory':
            s = v
        elif v == True:
            s = '--{k}'.format(k=k)
        else:
            s = '--{k}={v}'.format(k=k, v=v)
        return s
    # make a big chain of args
    minpower_call.extend(sorted(
        [arg2str(k, v) for k, v in minpower_args.iteritems() if
            (k == 'directory') or (
                (k in default_minpower_config) and
                (v != default_minpower_config[k])
        )
        ]))

    mode = args.scheduler_mode
    if mode == 'pass':
        # just let all the commands pass through
        pass
    elif mode == 'nohup':
        scheduler_call = ['nohup']
        if args.dry_run:
            print("would have opened files to write" +
                  "\n\tstdout: {p}.out\n\tstderr: {p}.err".format(p=os.getpid()))
        else:
            stdout = open('{}.out'.format(os.getpid()), 'w')
            stderr = open('{}.err'.format(os.getpid()), 'w')
    elif mode == 'qsub':
        # see https://sig.washington.edu/itsigs/Hyak_Job_Scheduler
        # default walltime limit is only one hour - must set this
        scheduler_call = ['qsub',
                          '-l nodes=1:ppn=12,feature=12core,mem={m}gb,walltime={h}:00:00'.format(
                              m=args.memory, h=args.hours_limit),
                          ]

        if args.email:
            scheduler_call.extend([
                '-m ae',  # mail on completion/failure
                '-M {e}'.format(e=args.email)
            ])

        # need to write a script to disk to call with qsub
        if minpower_args['standalone_restart']:
            # write to the same script, but comment out the original call
            script_name = './{}.sh'.format(minpower_args['pid'])
            if args.dry_run:
                print('would have commented out the original call in {}'.format(script_name))
            else:
                with open(script_name, 'r') as f:
                    old_script = '\n'.join(
                        ['# original call'] +
                        ['#' + ln for ln in f.readlines()] +
                        ['', ''])
                with open(script_name, 'w') as f:
                    f.write(old_script)
            script_mode = 'a'
        else:
            script_name = './{}.sh'.format(os.getpid())
            script_mode = 'w+'
        if args.dry_run:
            print('would have written script {f}: \n{c}'.format(
                f=script_name,
                c=' '.join(minpower_call)))
        else:
            with open(script_name, script_mode) as f:
                f.write(' '.join(minpower_call))
        minpower_call = [script_name]

    # actually make the call
    if args.dry_run:
        print('would have executed as a {p}:\n{c}'.format(
            p='child process' if mode == 'pass' else 'subprocess',
            c=' '.join((scheduler_call + minpower_call))
        ))
    else:
        if mode == 'pass':
            subprocess.call(scheduler_call + minpower_call)
            pid = None
        else:

            pid = subprocess.Popen(scheduler_call + minpower_call,
                                   stdout=stdout,
                                   stderr=stderr,
                                   ).pid

    if args.verbose:
        print 'parent process {}'.format(os.getpid())
        print 'starting run {}'.format(pid)


if __name__ == '__main__':
    main()
