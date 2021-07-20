from vbench.api import Benchmark, GitRepo
from datetime import datetime

import os

modules = [
    'unit_commitment',
    'data_in_out'
    ]

by_module = {}
benchmarks = []

for modname in modules:
    ref = __import__(modname)
    by_module[modname] = [v for v in list(ref.__dict__.values())
                          if isinstance(v, Benchmark)]
    benchmarks.extend(by_module[modname])

for bm in benchmarks:
    assert(bm.name is not None)

import getpass
import sys

USERNAME = getpass.getuser()

if sys.platform == 'darwin':
    HOME = '/Users/%s' % USERNAME
else:
    HOME = '/home/%s' % USERNAME


REPO_PATH = '/home/adam/minpower'
REPO_URL = 'git@github.com:adamgreenhall/minpower.git'
DB_PATH = os.path.join(REPO_PATH,'speed_check/benchmarks.db')
TMP_DIR = os.path.join(REPO_PATH,'tmp_build')

PREPARE = """
python setup.py clean
"""
BUILD = """
python setup.py build_ext --inplace
"""
START_DATE = datetime(2012, 12, 11)

dependencies = ['minpower_benchmark_utils.py']

repo = GitRepo(REPO_PATH)

def make_plots(benchmarks):
    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt

    vb_path = os.path.join(REPO_PATH, 'speed_check')
    fig_base_path = os.path.join(vb_path, 'figures')

    if not os.path.exists(fig_base_path):
        print('creating %s' % fig_base_path)
        os.makedirs(fig_base_path)

    for bmk in benchmarks:
        fig_full_path = os.path.join(fig_base_path, '%s.png' % bmk.name)

        # make the figure
        plt.figure(figsize=(10, 6))
        ax = plt.gca()
        bmk.plot(DB_PATH, ax=ax)

        start, end = ax.get_xlim()

        plt.xlim([start - 30, end + 30])
        plt.savefig(fig_full_path, bbox_inches='tight')
        plt.close('all')
        
if __name__ == '__main__':
    for bm in benchmarks:
        print(bm.name)
        print(bm.get_results(DB_PATH))
    make_plots(benchmarks)
