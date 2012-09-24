import os, sys, shutil, glob

build_dir = os.path.expanduser('~/research/minpower-doc/')

print 'building to',build_dir

def check_build():
    build_dirs = ['doctrees', '_static']
    for d in build_dirs:
        try:
            os.mkdir(build_dir+d)
        except OSError:
            pass

def css():
    check_build()
    if os.system('compass compile'):
        raise SystemExit('building css failed')
    os.system('cp source/_static/default.css {bd}_static/default.css'.format(bd=build_dir))

def html():    
    css()
    check_build()
    
    if os.system('sphinx-build -P -b html -d {build_dir}doctrees  source {build_dir}'.format(build_dir=build_dir)):
        raise SystemExit("Building HTML failed.")

def publish():
    os.system('git checkout gh-pages; git rebase master')
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

