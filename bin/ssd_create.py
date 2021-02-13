#!/usr/bin/python
import argparse,os,os.path,sys,struct,glob,collections

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")
    
    sys.exit(1)

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

def get_data(xs):
    data=""
    for x in xs:
        if type(x) is int or type(x) is long:
            assert x>=0 and x<=255
            data+=chr(x)
        elif type(x) is str:
            assert len(x)==1
            data+=x
        else:
            assert False,(x,type(x))

    return data

##########################################################################
##########################################################################

BeebFile=collections.namedtuple('Metadata','pc_path dir name load exec_ locked data')

File=collections.namedtuple('File','pc_path beeb_name')

##########################################################################
##########################################################################

def get_files(options):
    files=[]

    for rename in options.renames:
        files.append(File(pc_path=rename[0],beeb_name=rename[1]))

    # Use glob.glob on the input file names, since Windows-style
    # shells don't do that for you.
    for pattern in options.fnames:
        for path in glob.glob(pattern):
            files.append(File(pc_path=path,beeb_name=None))

    return files

##########################################################################
##########################################################################

def get_beeb_files(files):
    beeb_names_seen_lc=set()
    inf_paths_seen=set()

    result=[]
    for file in files:
        # don't treat used .inf paths as Beeb files!
        if file.pc_path in inf_paths_seen: continue
        
        inf_path='%s.inf'%file.pc_path

        inf_data=None
        if os.path.isfile(inf_path):
            inf_paths_seen.add(inf_path)
            with open(inf_path,'rt') as f:
                inf_lines=f.readlines()
                if len(inf_lines)>0: inf_data=inf_lines[0].split()

        if inf_data is None:
            inf_data=[os.path.basename(file.pc_path),
                      'ffffffff',
                      'ffffffff']

        if file.beeb_name is not None: beeb_name=file.beeb_name
        else: beeb_name=inf_data[0]

        if len(beeb_name)<3:
            print>>sys.stderr,'NOTE: Ignoring %s: BBC name too short: %s'%(file.pc_path,beeb_name)
            continue
        
        if beeb_name[1]!='.':
            print>>sys.stderr,'NOTE: Ignoring %s: BBC name not a DFS-style name: %s'%(file.pc_path,beeb_name)
            continue
        
        if len(beeb_name)>9:
            print>>sys.stderr,'NOTE: Ignoring %s: BBC name too long: %s'%(file.pc_path,beeb_name)
            continue

        load=int(inf_data[1],16)

        exec_=int(inf_data[2],16)

        locked=False
        if len(inf_data)>=4:
            if inf_data[3].lower()=='l': locked=True
            else:
                try:
                    attr=int(inf_data[3],16)
                    locked=(attr&8)!=0
                except ValueError: pass

        with open(file.pc_path,'rb') as f: data=[ord(x) for x in f.read()]

        result.append(BeebFile(pc_path=file.pc_path,
                               dir=beeb_name[0],
                               name=beeb_name[2:],
                               load=load,
                               exec_=exec_,
                               locked=locked,
                               data=data))

    return result

##########################################################################
##########################################################################

def get_boot_beeb_file(lines):
    if len(lines)==0: return None
    else:
        data=''
        for line in lines: data+=line+'\r'

        return BeebFile(pc_path='<<command line>>',
                        dir='$',
                        name='!BOOT',
                        load=0xffffffff,
                        exec_=0xffffffff,
                        locked=True,
                        data=data)

##########################################################################
##########################################################################

def get_unique_paths(files):
    result=[]
    
    abs_paths_seen=set()
    for file in files:
        abs_path=os.path.normcase(os.path.abspath(file.pc_path))
        if abs_path not in abs_paths_seen:
            result.append(file)
            abs_paths_seen.add(abs_path)

    return result

##########################################################################
##########################################################################

# def get_size_sectors(size_bytes): return (size_bytes+255)//256

FileRegion=collections.namedtuple('FileRegion','sector num_sectors')

def ssd_create(options):
    global g_verbose
    g_verbose=options.verbose

    files=get_files(options)

    files=get_beeb_files(files)

    # *TITLE setting.
    title=''
    if options.title is None:
        title_name=os.path.join(options.dir,'.title')
        if os.path.isfile(title_name):
            with open(title_name,'rt') as f: title=f.readlines()[0][:12]
    else:
        if len(options.title)>12: fatal("title is too long - max 12 chars")
        # if len(options.fnames)>31: fatal("too many files - max 31")
        title=options.title

    # *OPT4 setting.
    opt4=0
    if options.opt4 is None:
        if options.dir is not None:
            opt4_name=os.path.join(options.dir,'.opt4')
            if os.path.isfile(opt4_name):
                with open(opt4_name,'rb') as f: opt4=int(f.read()[0])&3
    else:
        if options.opt4<0 or options.opt4>3:
            fatal("bad *OPT4 value: %s"%options.opt4)
        opt4=options.opt4

    if len(options.build)>0:
        opt4=3

    # How many usable sectors on this disc?
    num_disc_sectors=(40 if options._40 else 80)*10
    v("%d sector(s) on disc\n"%num_disc_sectors)

    # Add a manually-specified !BOOT, if necessary.
    boot_file=get_boot_beeb_file(options.build)
    if boot_file is not None: files=[boot_file]+files

    if len(files)>31:
        fatal('Too many files - disk has %d files, but max is 31'%len(files))

    next_sector=2
    file_regions=[]

    for file in files:
        region=FileRegion(sector=next_sector,
                        num_sectors=(len(file.data)+255)//256)
        file_regions.append(region)
        next_sector+=region.num_sectors

        v("    %s.%-8s %08X %08X %08X %s "%(file.dir,
                                            file.name,
                                            file.load,
                                            file.exec_,
                                            len(file.data),
                                            "L" if file.locked else ""))

        v(" @%d"%region.sector)

        v("\n")

    if next_sector>num_disc_sectors-2:
        fatal("Too much data - disk has %d sectors, but files use %d sectors"%(num_disc_sectors,next_sector))

    # Create catalogue.
    sectors=[[0]*8+[" "]*248,
             [0]*256]

    # Store title.
    for i in range(len(title)):
        if i<8: sectors[0][i]=title[i]
        else: sectors[1][i-8]=title[i]

    # Store metadata.
    sectors[1][4]=0                 # Disk write count
    sectors[1][5]=len(files)*8
    sectors[1][6]=((opt4<<4)|
                   ((num_disc_sectors>>8)&3))
    sectors[1][7]=num_disc_sectors&255

    # Store catalogue data.
    next_sector=2
    for i,file in enumerate(files):
        region=file_regions[i]
        
        # Files are stored in reverse sector order.
        offset=8+8*(len(files)-1-i)

        for j in range(len(file.name)): sectors[0][offset+j]=file.name[j]
        sectors[0][offset+7]=file.dir

        sectors[1][offset+0]=(file.load>>0)&255
        sectors[1][offset+1]=(file.load>>8)&255
        sectors[1][offset+2]=(file.exec_>>0)&255
        sectors[1][offset+3]=(file.exec_>>8)&255
        sectors[1][offset+4]=(len(file.data)>>0)&255
        sectors[1][offset+5]=(len(file.data)>>8)&255
        sectors[1][offset+6]=(((3 if (file.exec_&0xffff0000) else 0)<<6)|
                              (((len(file.data)>>16)&3)<<4)|
                              ((3 if (file.load&0xffff0000) else 0)<<2)|
                              (((region.sector>>8)&3)<<0))
        sectors[1][offset+7]=region.sector&255

    # Store file data
    for i,file in enumerate(files):
        region=file_regions[i]
        
        assert len(sectors)==region.sector
        for i in range(region.num_sectors):
            sectors.append(list(file.data[i*256:i*256+256]))

        # The last sector might need padding.
        while len(sectors[-1])!=256: sectors[-1].append(0)

    v("%d sectors on disc\n"%len(sectors))

    image="".join([get_data(x) for x in sectors])

    v("%d bytes in disc image\n"%len(image))

    if options.output_fname is not None:
        with open(options.output_fname,"wb") as f: f.write(image)
        
##########################################################################
##########################################################################

def main(args):
    parser=argparse.ArgumentParser(description="make SSD disc image from .inf folder")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")
    
    parser.add_argument("--40",
                        dest="_40",
                        default=False,
                        action="store_true",
                        help="create a 40- rather than 80-track disk")

    parser.add_argument("-t",
                        "--title",
                        metavar="TITLE",
                        default="",
                        help="use %(metavar)s as disc title (overrides --dir)")

    parser.add_argument("-4",
                        "--opt4",
                        metavar="VALUE",
                        default=None,
                        type=int,
                        help="set *OPT4 option to %(metavar)s (overrides --dir)")

    parser.add_argument('-d',
                        '--dir',
                        metavar='PATH',
                        default=None,
                        help='if specified, read *OPT4 and title settings from BeebLink folder %(metavar)s (title will be silently truncated if too long)')

    parser.add_argument("-o",
                        dest="output_fname",
                        metavar="FILE",
                        default=None,
                        help="write result to FILE")

    parser.add_argument('-r',
                        dest='renames',
                        metavar=('PC-FILE','BBC-NAME'),
                        nargs=2,
                        action='append',
                        default=[],
                        help='add PC-FILE under BBC name BBC-NAME')

    parser.add_argument('-b',
                        '--build',
                        action='append',
                        default=[],
                        help='add line to $.!BOOT, overriding any $.!BOOT specified and placing file first on disk. Implies --opt4=3')

    parser.add_argument("fnames",
                        nargs="*",
                        metavar="FILE",
                        #action="append",
                        default=[],
                        help="file(s) to put in disc image (non-BBC files will be ignored)")
    
    options=parser.parse_args(args)
    ssd_create(options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
