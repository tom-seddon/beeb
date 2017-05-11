#!env python
import argparse,os,os.path,sys,struct
emacs=os.getenv("EMACS") is not None

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

ascii_by_65link={
    "_sp":" ",
    "_xm":"!",
    "_dq":"\"",
    "_ha":"#",
    "_do":"$",
    "_pc":"%",
    "_am":"&",
    "_sq":"'",
    "_rb":"(",
    "_lb":")",
    "_as":"*",
    "_pl":"+",
    "_cm":",",
    "_mi":"-",
    "_pd":".",
    "_fs":"/",
    "_co":":",
    "_sc":";",
    "_st":"<",
    "_eq":"=",
    "_lt":">",
    "_qm":"?",
    "_at":"@",
    "_hb":"[",
    "_bs":"\\",
    "_bh":"]",
    "_po":"^",
    "_un":"_",
    "_bq":"`",
    "_cb":"{",
    "_ba":"|",
    "_bc":"}",
    "_no":"~",
}

def get_bbc_name(x):
    r=""
    i=0
    while i<len(x):
        if x[i]=="_":
           code=x[i:i+3]
           if code not in ascii_by_65link: fatal("bad 65link name: %s"%x)
           r+=ascii_by_65link[code]
           i+=3
        else:
            r+=x[i]
            i+=1
        

    return r

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

# def get_size_sectors(size_bytes): return (size_bytes+255)//256

class File: pass

def main(options):
    global g_verbose
    g_verbose=options.verbose
    
    # Remove input files with an extension - this just makes it easier
    # to use from a POSIX-style shell.
    options.fnames=[x for x in options.fnames if os.path.splitext(x)[1]==""]

    # Basic options check.
    if len(options.title)>12: fatal("title is too long - max 12 chars")
    if len(options.fnames)>31: fatal("too many files - max 31")

    options.opt4=int(options.opt4)
    if not (options.opt4>=-1 and options.opt4<=3): fatal("bad *OPT4 value: %s"%options.opt4)

    # How many usable sectors on this disc?
    num_disc_sectors=(40 if options._40 else 80)*10
    v("%d sector(s) on disc\n"%num_disc_sectors)
    
    # Load all files in.
    files=[]
    next_sector=2
    v("%d file(s):\n"%len(options.fnames))
    for fname in options.fnames:
        file=File()

        file.bbc_name=get_bbc_name(os.path.split(fname)[1])
        if len(file.bbc_name)>8: fatal("file name too long: %s"%fname)
        with open(fname,"rb") as f: file.data=f.read()

        file.load=0
        file.exec_=0
        file.locked=False

        lea_fname=fname+".lea"
        if os.path.isfile(lea_fname):
            with open(lea_fname,"rb") as f: lea_data=f.read()
            if len(lea_data)!=12: fatal("bad LEA file: %s"%lea_fname)
            file.load,file.exec_,a=struct.unpack("<III",lea_data)
            file.locked=(a&8)!=0

        file.sector=next_sector
        file.size_sectors=(len(file.data)+255)//256
        next_sector+=file.size_sectors

        v("    %-10s %08X %08X %08X %s "%(file.bbc_name[0]+"."+file.bbc_name[1:],
                                         file.load,
                                         file.exec_,
                                         len(file.data),
                                         "L" if file.locked else ""))

        v(" @%d"%file.sector)

        v("\n")

        files.append(file)

    if next_sector>num_disc_sectors-2: fatal("Too much data - disk has %d sectors, but files use %d sectors"%(num_disc_sectors,next_sector))

    # Create catalogue.
    sectors=[[0]*8+[" "]*248,
             [0]*256]

    # Store title.
    for i in range(len(options.title)):
        if i<8: sectors[0][i]=options.title[i]
        else: sectors[1][i-8]=options.title[i]

    # Store metadata.
    sectors[1][4]=0                 # Disk write count
    sectors[1][5]=len(files)*8
    sectors[1][6]=((options.opt4<<4)|
                   ((num_disc_sectors>>8)&3))
    sectors[1][7]=num_disc_sectors&255

    # Store catalogue data.
    next_sector=2
    for i,file in enumerate(files):
        offset=8+8*i

        for j in range(1,len(file.bbc_name)): sectors[0][offset+j-1]=file.bbc_name[j]
        sectors[0][offset+7]=file.bbc_name[0]

        sectors[1][offset+0]=(file.load>>0)&255
        sectors[1][offset+1]=(file.load>>8)&255
        sectors[1][offset+2]=(file.exec_>>0)&255
        sectors[1][offset+3]=(file.exec_>>8)&255
        sectors[1][offset+4]=(len(file.data)>>0)&255
        sectors[1][offset+5]=(len(file.data)>>8)&255
        sectors[1][offset+6]=(((3 if (file.exec_&0xffff0000) else 0)<<6)|
                              (((len(file.data)>>16)&3)<<4)|
                              ((3 if (file.load&0xffff0000) else 0)<<2)|
                              (((file.sector>>8)&3)<<0))
        sectors[1][offset+7]=file.sector&255

    # Store file data
    for file in files:
        assert len(sectors)==file.sector
        for i in range(file.size_sectors):
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

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="make SSD disc image from 65link folder")

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
                        help="use TITLE as disc title")

    parser.add_argument("-4",
                        "--opt4",
                        metavar="VALUE",
                        default=0,
                        help="set *OPT4 option to VALUE")

    parser.add_argument("-o",
                        dest="output_fname",
                        metavar="FILE",
                        default=None,
                        help="write result to FILE")

    parser.add_argument("fnames",
                        nargs="+",
                        metavar="FILE",
                        #action="append",
                        default=[],
                        help="65link file(s) to put in disc image (if list includes .LEA files, they will be ignored)")
    
    args=sys.argv[1:]

    options=parser.parse_args(args)
    main(options)
    
