import os, subprocess, sys
import glob

def main(publish=False):
    if not os.getcwd().endswith('doc'): os.chdir('./doc')
    os.system('make html')
    #os.system('make latexpdf')
    for f in glob.glob('*.log'): os.remove(f)
    for f in glob.glob('../*.pyc'): os.remove(f)

if __name__ == "__main__": 
    ''' command line input'''
    if len(sys.argv)==1: main()
    elif len(sys.argv)==2: 
        ifpub=sys.argv[1] == 'publish'
        main(publish=ifpub)
    else: 
        raise OSError('build takes 0 or 1 arguments')

