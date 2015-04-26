#!/usr/bin/python
import sys,os,os.path,argparse,struct

##########################################################################
##########################################################################

def main(options):
    lea_fname=options.fname+".lea"

    if os.path.isfile(lea_fname):
        with open(lea_fname,"rb") as f: lo,ex,at=struct.unpack("<III",f.read())
        found_lea=True
    else:
        lo,ex,at=0,0,0
        found_lea=False

    if options.dump:
        if not found_lea: print "No LEA file found."
        else: print "Load: 0x%08X; Exec: 0x%08X; Attributes: 0x%08X (%s)"%(lo,ex,at,"locked" if at&8 else "unlocked")

    modified=False

    if options.load is not None:
        lo=options.load
        modified=True
    
    if options.exec_ is not None:
        ex=options.exec_
        modified=True
    
    if options.io:
        lo|=0xFFFF0000
        ex|=0xFFFF0000
        modified=True

    if modified:
        with open(lea_fname,"wb") as f: f.write(struct.pack("<III",lo,ex,at))

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="set BBC file load/exec/attributes")

    parser.add_argument("-d",
                        "--dump",
                        action="store_true",
                        help="print old values")

    parser.add_argument("-e",
                        "--exec",
                        dest="exec_",
                        type=auto_int,
                        default=None,
                        help="new execution address, if any")

    parser.add_argument("-l",
                        "--load",
                        type=auto_int,
                        default=None,
                        help="new load address, if any")

    parser.add_argument("--io",
                        default=False,
                        action="store_true",
                        help="set top 32 bits of load/exec, so  file loads and runs in I/O processor")

    parser.add_argument("fname",
                        metavar="FILE",
                        help="65link file to modify")

    main(parser.parse_args(sys.argv[1:]))
    
