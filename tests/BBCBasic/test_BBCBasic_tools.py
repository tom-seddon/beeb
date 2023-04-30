#!/usr/bin/python3
import sys,os,os.path,argparse,json,hashlib,collections,subprocess

sys.path.append(os.path.join(sys.path[0],'../../bin/'))
import BBCBasicToText

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.stderr.flush()
    sys.exit(1)

##########################################################################
##########################################################################

def load_beeblink_config(path):
    folders=[]
    with open(path,'rt') as f: j=json.load(f)
    folders+=j.get('folders',[])
    folders+=j.get('tube_host_folders',[])
    return folders

##########################################################################
##########################################################################

def get_basic_size(b):
    i=0

    while True:
        if i>=len(b): return None   # hit EOF before EOP marker
        if b[i]!=13: return None    # invalid structure
        if i+1>=len(b): return None # line past EOF
        if b[i+1]==0xff: return i+2 # EOP marker - valid
        if i+3>=len(b): return None # line header past EOF
        if b[i+3]==0: return None   # invalid line length

        # Skip line
        i+=b[i+3]                    

##########################################################################
##########################################################################

UniqueBASICFile=collections.namedtuple('UniqueBASICFile','path data basic_size')

# embedded 
exclusions=set([
    # # embedded 0d ff
    # '5629d69f2becfc2d0cf3e0849af78ab8367d0aded5e5a1409d4f9f2ef780fd0c',
    # '5fcdcab2f69fb0181e1b0e5f075ce81f7d64faf79261107e26b88a1a1517b380',
    # '31275e8c40c3c4db5ba235763362e034f56271ecd46a2df07bd5f44f4ba7d437',

    # # embedded 0d
    # '47d3fd00a0198312f55eefa061c426a06829ad776b3d18ec159f7a6bdaa11016',
    # 'e2a8a887c0aa454ae48fab6d978178df00eabc1a05f650bf11df4c441e8c26e9',
    # 'df22851965a40e950073f77c82e543c47cf96e9bbaffb1696d415a685716652d',
    # 'e0bfff52fd0c60750e681da16aaecaa09ffd54f2ebe08f5e5a574c087093b3ca',
    # '01dcb56c2b8e6700823957790993fbb2289fa120d40df1c180587ea96ed35c9f',
    # '7d45c514bb51b5281340b8bafb4571374ed9c260b8baef351707fe8d34eed49e',
    # 'f8d3b1341bd8d67ff4c9f9875e076c9f040a47d62d5ae9cff67e073b6ddf72e1',
])

def main2(options):
    folders=[]
    if options.beeblink_config is not None:
        folders+=load_beeblink_config(options.beeblink_config)
    folders+=options.folders
    if len(folders)==0: fatal('no folders specified')

    total_num_files=0
    total_files_size=0

    total_extra_stripped=0
    
    total_num_basic_files=0
    total_basic_files_size=0

    unique_files_by_hash={}

    # BBCBasicToText has no specific limit, but basictool runs the
    # non-HI BASIC ROM in an emulator with PAGE=&E00.
    max_basic_size=0x8000-0xe00

    for folder in folders:
        for dirpath,dirnames,filenames in os.walk(folder):
            for filename in filenames:
                path=os.path.join(dirpath,filename)
                
                with open(path,'rb') as f:
                    total_num_files+=1
                    size=os.stat(f.fileno()).st_size
                    total_files_size+=size

                    if size>max_basic_size:
                        # too large for basictool!
                        continue
                    
                    if f.read(2)!=b'\x0d\x00':
                        # definitely not BBC BASIC!
                        continue
                    
                    f.seek(0)
                    data=f.read()

                basic_size=get_basic_size(data)
                if basic_size is not None:

                    hasher=hashlib.sha256()
                    hasher.update(data)
                    hash=hasher.hexdigest()

                    if hash in exclusions:
                        # ignoring this one
                        continue

                    total_num_basic_files+=1
                    total_basic_files_size+=len(data)
                    
                    if hash not in unique_files_by_hash:
                        unique_files_by_hash[hash]=UniqueBASICFile(path,data,basic_size)

    print('found %d/%d unique BBC BASIC files'%(len(unique_files_by_hash),
                                                total_num_basic_files))

    if options.output_folder is not None:
        basictool_failures=[]
        mismatches=[]

        bbtt_args=['--codes','--perfect']
        bt_args=['--ascii','--input-tokenised']
        
        if not os.path.isdir(options.output_folder):
            os.makedirs(options.output_folder)

        unique_files=[kv for kv in unique_files_by_hash.items()]

        mismatches=''
        num_mismatches=0

        for i,kv in enumerate(unique_files):
            original_path=os.path.join(options.output_folder,
                                       '%s.original.dat'%kv[0])
            stripped_path=os.path.join(options.output_folder,
                                       '%s.stripped.dat'%kv[0])

            if sys.stdout.isatty():
                sys.stdout.write('\r%d/%d: %s (mismatches=%d)'%(i,len(unique_files),original_path,num_mismatches))
                sys.stdout.flush()
            
            with open(original_path,'wb') as f: f.write(kv[1].data)

            with open(stripped_path,'wb') as f:
                if kv[1].basic_size==len(kv[1].data): f.write(kv[1].data)
                else: f.write(kv[1].data[:kv[1].basic_size])

            for basic2 in [False,True]:
                ver='basic2' if basic2 else 'basic4'
                bbtt_text_path=os.path.join(options.output_folder,'%s.BBCBasicToText.%s.txt'%(kv[0],ver))
                BBCBasicToText.main(bbtt_args+[original_path,bbtt_text_path])

                bt_text_path=os.path.join(options.output_folder,'%s.basictool.%s.txt'%(kv[0],ver))
                cmd_line=['basictool']+bt_args+[original_path,bt_text_path]
                retcode=subprocess.call(cmd_line,shell=False)
                if retcode!=0: basictool_failures.append(i)

                # safest to treat the output as binary, on account of the
                # possibility of embedded control codes.
                with open(bt_text_path,'rb') as f: bt_data=f.read()
                with open(bbtt_text_path,'rb') as f: bbtt_data=f.read()

                if bbtt_data!=bt_data:
                    mismatches+='** %s (%s)\n'%(kv[0],ver)
                    mismatches+='  vbindiff %s %s\n'%(bbtt_text_path,bt_text_path)
                    mismatches+='  (%d BASIC bytes; original path: %s)\n'%(kv[1].basic_size,kv[1].path)
                    
                    num_mismatches+=1
        print()

        if len(basictool_failures)>0:
            print('basictool failures:')
            for i in basictool_failures: print('  %s'%unique_files[i][0])

        if len(mismatches)>0:
            print('mismatches:')
            print(mismatches)
            print('%d mismatches'%num_mismatches)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-o','--output-folder',metavar='FOLDER',default='./corpus',help='''output corpus to %(metavar)s. Default: %(default)s''')

    parser.add_argument('-b','--beeblink-config',metavar='PATH',help='''read BeebLink config from %(metavar)s and look for BBC BASIC file(s) in its volume folders''')

    parser.add_argument('folders',nargs='*',metavar='PATH',help='''look for BBC BASIC file(s) in %(metavar)s''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
