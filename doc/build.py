import os, sys, shutil, glob

def check_build():
    build_dirs = [
        'build', 'build/doctrees', 'build/html',
        'build/html/_static']
    for d in build_dirs:
        try:
            os.mkdir(d)
        except OSError:
            pass

def clean():
    if os.path.exists('build'):
        shutil.rmtree('build')

def css():
    check_build()
    if os.system('compass compile'):
        raise SystemExit('building css failed')
    # os.system('cp source/_static/default.css build/html/_static/default.css')

def html():    
    css()
    check_build()    
    if os.system('sphinx-build -P -b html -d build/doctrees  source build/html'):
        raise SystemExit("Building HTML failed.")

def publish():
    os.system('git checkout gh-pages')
    html()
    os.system('git commit -a')
    os.system('git push origin gh-pages')
    os.system('git checkout master')

def main(publish=False,just_css=False):
    if not os.getcwd().endswith('doc'): os.chdir('./doc')
    if just_css: css()
    if publish: publish()
    else: html()
    
if __name__ == "__main__": 
    ''' command line input'''
    if len(sys.argv)==1: main()
    elif len(sys.argv)==2: 
        publish= str(sys.argv[1]).strip() == 'publish'
        just_css= str(sys.argv[1]).strip() == 'css'
        main(publish=publish,just_css=just_css)
        
        
    else: 
        raise OSError('build takes 0 or 1 arguments')

