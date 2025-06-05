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
for parts_log2 in range(8):
    g_tests.append(Test(hash='f39105d3ae20af30516031e1b998d4e0f2052a97',
                        parts=1<<parts_log2))

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
        run(['git','reset','--hard'])
        run(['git','checkout',test.hash])
        run(['git','submodule','update'])

        if test.parts is not None:
            run([make_path,'update_mfns','NUM_GROUPS=%d'%test.parts])

        if windows: run([make_path,'init_vs2019'])
        else: run([make_path,'init'])

        def run2(config,folder):
            # Rebuild config
            if windows:
                os.chdir(os.path.join(b2_path,'build/vs2019'))
                save_time(config,'Rebuild',
                          run([devenv_path,'/Rebuild',config,'b2.sln']))
            else:
                os.chdir(os.path.join(b2_path,'build/%s.%d'%(folder,
                                                             suffix)))
                run(['ninja','clean'])
                save_time('Rebuild %s'%config,
                          run(['ninja']))

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
