#!/usr/bin/python3
import sys,os,os.path,argparse,subprocess,time,collections,platform,pathlib

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

Test=collections.namedtuple('Test','hash parts')

# List of commits to get, and optional number of parts to try with for
# each commit.

g_tests=[]
# for parts_log2 in range(8):
#     g_tests.append(Test(hash='f39105d3ae20af30516031e1b998d4e0f2052a97',
#                         parts=1<<parts_log2))

##########################################################################
##########################################################################

#  (let* ((vswhere-path "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"))
# (when-let* ((lines (process-lines vswhere-path
# "-version" (format "%d" version)
# "-property" "installationPath"))

def run(argv):
    start_pc=time.perf_counter()
    subprocess.run(argv,check=True)
    total_pc=time.perf_counter()-start_pc
    return total_pc

def git_reset():
    run(['git','reset','--hard'])
    run(['git','clean','-f'])

def capture(argv):
    result=subprocess.run(argv,check=True,capture_output=True,encoding='utf-8')
    return result.stdout.splitlines()

def main2(options):
    macos=False
    linux=False
    windows=False
    if platform.system()=='Windows': windows=True
    elif platform.system()=='Darwin':
        macos=True
        suffix='osx'
    else:
        linux=True              # the only other option, of course
        suffix='linux'

    b2_path=os.path.abspath(options.b2_path)
    
    if windows:
        vs_path=capture(['C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe',
                         '-version','16',
                         '-property','installationPath'])[0].strip()
        devenv_path=os.path.join(vs_path,'Common7/IDE/devenv.com')
        make_path=os.path.join(b2_path,'bin\snmake.exe')
    else:
        make_path='make'

    if options.output_path is None: output_path=None
    else:
        output_path=os.path.abspath(options.output_path)
        with open(output_path,'wt') as f: pass

    os.chdir(b2_path)

    if len(capture(['git','status','--porcelain']))!=0:
        fatal('b2 working copy not clean: %s'%b2_path)

    branch_name=capture(['git','branch','--show-current'])[0]
    if len(branch_name)==0:
        fatal('no branch name for working copy (detached head?): %s'%b2_path)
    
    for i in range(8): g_tests.append(Test(hash=branch_name,parts=1<<i))

    for test in g_tests:
        def save_time(config,description,time):
            if output_path is None: return
            
            with open(output_path,'at') as f:
                f.write('%s,%d,%s,%s,%d\n'%(test.hash,
                                            0 if test.parts is None else test.parts,
                                            config,
                                            description,
                                            time))

        os.chdir(b2_path)
        git_reset()
        run(['git','checkout',test.hash])
        run(['git','submodule','update'])

        if test.parts is not None:
            run([make_path,'update_mfns','NUM_GROUPS=%d'%test.parts])

        if windows: run([make_path,'init_vs2019'])
        else: run([make_path,'-j','_unixd','_unixr','_unixf'])

        def run2(config,folder):
            # Rebuild config
            if windows:
                os.chdir(os.path.join(b2_path,'build/vs2019'))
                save_time(config,'Rebuild',
                          run([devenv_path,'/Rebuild',config,'b2.sln']))
            else:
                os.chdir(os.path.join(b2_path,'build/%s.%s'%(folder,
                                                             suffix)))
                run(['ninja','clean'])
                save_time(config,'Rebuild',run(['ninja']))

            # Touch BBCMicro.h
            best_time=None
            for i in range(2):
                path=pathlib.Path(os.path.join(b2_path,'src/beeb/include/beeb/BBCMicro.h'))
                print(path)
                path.touch()
                if windows: time=run([devenv_path,'/build',config,'b2.sln'])
                else: time=run(['ninja'])

                if best_time is None or time<best_time: best_time=time

            save_time(config,'Touch BBCMicro.h',best_time)

            if windows:
                # monitor annoying per-run overhead
                save_time(config,'No-op run',run([devenv_path,'/build',config,'b2.sln']))

        run2('Debug','d')
        run2('RelWithDebInfo','r')

    git_reset()

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('--b2',dest='b2_path',metavar='PATH',required=True,help='''find b2 working copy on %(metavar)s''')
    parser.add_argument('-o','--output',dest='output_path',metavar='FILE',help='''write log to %(metavar)s''')
    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
