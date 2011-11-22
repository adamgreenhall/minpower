import os, subprocess, sys
import glob

def main(publish=False,just_css=False):
    if not os.getcwd().endswith('doc'): os.chdir('./doc')
    if just_css:
        os.system('compass compile')
        os.system('cp _static/default.css _build/html/_static/default.css')
        return
    if publish:
        os.system('make gh-pages')
    else:
        os.system('compass compile')
        os.system('make html')
        #os.system('make latexpdf')
        for f in glob.glob('*.log'): os.remove(f)
        for f in glob.glob('../*.pyc'): os.remove(f)
    
if __name__ == "__main__": 
    ''' command line input'''
    if len(sys.argv)==1: main()
    elif len(sys.argv)==2: 
        publish= str(sys.argv[1]).strip() == 'publish'
        just_css= str(sys.argv[1]).strip() == 'css'
        main(publish=publish,just_css=just_css)
        
        
    else: 
        raise OSError('build takes 0 or 1 arguments')

