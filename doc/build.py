import os, sys, shutil, glob

build_dir = os.path.expanduser('~/research/minpower-doc/')
project_dir = os.path.expanduser('~/minpower/')



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

def api():
    print('autogenerating API')
    os.system('rm {proj}/doc/source/api/*.rst'.format(proj=project_dir))
    os.system('sphinx-apidoc {proj}/minpower -o {proj}/doc/source/api'.format(proj=project_dir))

def html():
    print 'building to',build_dir
    css()
    check_build()
    api()
    
    if os.system('sphinx-build -P -b html -d {build_dir}doctrees  source {build_dir}'.format(build_dir=build_dir)):
        raise SystemExit("Building HTML failed.")

def publish():
    print 'publishing docs from ',build_dir
    current_dir = os.getcwd()
    os.chdir(build_dir)
    os.system('git commit -a')
    os.system('git push origin gh-pages')
    os.chdir(current_dir)

def main(publish=False,just_css=False):
    if not os.getcwd().endswith('doc'): os.chdir('./doc')
    if just_css: css()
    if publish: publish()
    else: html()
    
if __name__ == "__main__": 
    ''' command line input'''
    if len(sys.argv)==1: main()
    elif len(sys.argv)==2: 
        command = str(sys.argv[1]).strip() 
        if command == 'publish':
            publish()
        elif command == 'css':
            css()
    else: 
        raise OSError('build takes 0 or 1 arguments')

