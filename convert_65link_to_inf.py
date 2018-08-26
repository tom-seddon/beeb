#!/usr/bin/python
import os,os.path,sys,argparse,glob,struct,shutil

##########################################################################
##########################################################################

emacs=os.getenv('INSIDE_EMACS') is not None

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")
    
    if emacs: raise RuntimeError
    else: sys.exit(1)

##########################################################################
##########################################################################

g_verbose=False

def v(str):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(str)
        sys.stdout.flush()

##########################################################################
##########################################################################

bbc_char_from_65link_code={
    "_sp":" ", "_xm":"!", "_dq":"\"",
    "_ha":"#", "_do":"$", "_pc":"%", "_am":"&", "_sq":"'", "_rb":"(",
    "_lb":")", "_as":"*", "_pl":"+", "_cm":",", "_mi":"-", "_pd":".",
    "_fs":"/", "_co":":", "_sc":";", "_st":"<", "_eq":"=", "_lt":">",
    "_qm":"?", "_at":"@", "_hb":"[", "_bs":"\\", "_bh":"]", "_po":"^",
    "_un":"_", "_bq":"`", "_cb":"{", "_ba":"|", "_bc":"}", "_no":"~",
}

##########################################################################
##########################################################################

# returns None if the file obviously wasn't created by 65Link.
#
# Otherwise returns all the chars, no dir separator - e.g., $.!BOOT is
# $!BOOT
def get_bbc_name_from_65link_name(pc_file_name):
    bbc_name=''
    i=0
    while i<len(pc_file_name):
        c=pc_file_name[i]
        if c.isalnum():
            bbc_name+=c
            i+=1
        elif c=='_':
           code=pc_file_name[i:i+3]
           if code not in bbc_char_from_65link_code: return None
           bbc_name+=bbc_char_from_65link_code[code]
           i+=3
        else: return None

    if len(bbc_name)<2: return None

    return bbc_name

##########################################################################
##########################################################################

# 
def get_pc_name_from_bbc_name(bbc_file_name):
    invalid_chars="/"           # not valid on Windows or Unix.
    invalid_chars+="<>:\"\\|?*" # not valid on Windows.
    invalid_chars+=" ."         # not allowing these.
    invalid_chars+="#"          # the escape char must be escaped...

    pc_file_name=''
    for c in bbc_file_name:
        if ord(c)>255:
            pc_file_name+='#ff' # ugh, sorry.
        elif ord(c)<32 or ord(c)>=127 or c in invalid_chars:
            pc_file_name+='#%02x'%ord(c)
        else:
            pc_file_name+=c

    return pc_file_name[0]+'.'+pc_file_name[1:]
            

##########################################################################
##########################################################################

def main(options):
    global g_verbose;g_verbose=options.verbose

    # Pass 1 - find BBC files, and copy them across. If there's an
    # associated .lea file, do that too.

    lea_ext=os.path.normcase('.lea')
    inf_ext='.inf'

    ignore_files=['BootOpt','FnTrans']
    ignore_files=[os.path.normcase(x) for x in ignore_files]

    ignoring=[]

    # Copy the files.
    for dirpath,dirnames,filenames in os.walk(options.input_folder):
        for filename in filenames:
            if os.path.normcase(filename) in ignore_files: continue
            
            name,ext=os.path.splitext(filename)
            
            if ext!='':
                if os.path.normcase(ext)!=lea_ext:
                    ignoring.append(os.path.join(dirpath,filename))
                continue

            bbc_name=get_bbc_name_from_65link_name(name)
            if bbc_name is None:
                ignoring.append(os.path.join(dirpath,filename))
                continue

            pc_name=get_pc_name_from_bbc_name(bbc_name)

            # full input path.
            input_path=os.path.join(dirpath,filename)

            # full output path.
            output_path=os.path.join(os.path.relpath(dirpath,
                                                     options.input_folder),
                                     pc_name)
            
            if options.output_folder is not None:
                output_path=os.path.join(options.output_folder,
                                         output_path)

            # got an LEA file?
            lea_path=input_path+lea_ext
            inf=None
            if os.path.isfile(lea_path):
                with open(lea_path,'rb') as f: lea=f.read()
                if len(lea)==12:
                    load,exec_,attr=struct.unpack("<III",lea)
                    inf='%s.%s %08X %08X %s'%(bbc_name[0],
                                              bbc_name[1:],
                                              load,
                                              exec_,
                                              'L' if attr&8 else '')

            v('%s -> %s '%(input_path,output_path))
            if inf is None: v('(no inf)')
            else: v(inf)
            v('\n')
            
            # copy all this stuff across.
            if options.output_folder is not None:
                output_dir=os.path.dirname(output_path)
                if not os.path.isdir(output_dir): os.makedirs(output_dir)

                with open(input_path,'rb') as f: data=f.read()
                with open(output_path,'wb') as f: f.write(data)

                if inf is not None:
                    with open(output_path+inf_ext,'wt') as f:
                        print>>f,inf

    for x in ignoring: v('Ignoring: %s\n'%x)

    # Find the BootOpt files.
    bootopt_name=os.path.normcase('BootOpt')
    for dirpath,dirnames,filenames in os.walk(options.input_folder):
        for filename in filenames:
            if os.path.normcase(filename)!=bootopt_name: continue

            with open(os.path.join(dirpath,filename),'rb')as f:
                data=f.read()

            if len(data)!=8: continue

            v('%s:\n'%dirpath)

            for drive in range(8):
                opt=ord(data[drive])&3
                if opt!=0:
                    if options.output_folder is not None:
                        drive_folder=os.path.join(options.output_folder,
                                                  os.path.relpath(dirpath,
                                                                  options.input_folder),
                                                  '%d'%drive)
                        if os.path.isdir(drive_folder):
                            v('    %d: option = %d\n'%(drive,opt))
                            with open(os.path.join(drive_folder,
                                                   '.opt4'),'wt') as f:
                                print>>f,'%d'%opt

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="convert 65Link volumes to .INF format")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")

    parser.add_argument("-o",
                        dest="output_folder",
                        metavar="FOLDER",
                        default=None,
                        help="put INF files in %(metavar)s (will be created if it doesn't exist; source folder structure will be replicated)")

    parser.add_argument(dest="input_folder",
                        metavar="FOLDER",
                        help="read 65Link volumes from %(metavar)s")

    main(parser.parse_args(sys.argv[1:]))
