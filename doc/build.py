#!/usr/bin/env python
import os, subprocess
import glob
#if not os.getcwd().endswith('doc'): os.chdir('./doc')
os.system('make html')
#os.system('make latexpdf')
for f in glob.glob('*.log'): os.remove(f)
for f in glob.glob('../*.pyc'): os.remove(f)
