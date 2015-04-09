#!env python
import os,argparse,sys,hashlib

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")
    sys.exit(1)

def warn(str):
    sys.stderr.write("WARNING: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")

##########################################################################
##########################################################################

def p(x):
    sys.stdout.write(x)
    sys.stdout.flush()

##########################################################################
##########################################################################

def get_str(data,offset):
    result=""
    i=offset
    while i<len(data) and data[i]!=chr(0):
        result+=data[i]
        i+=1

    if i>=len(data): return None
    else: return result.encode("string_escape")

def not_rom(fname,reason): warn("Not a ROM (%s): %s"%(reason,fname))

def main(options):
    for fname in options.fnames:
        if not os.path.isfile(fname):
            warn("Not a file: %s\n"%fname)
            continue
        
        with open(fname,"rb") as f: data=f.read()
        bytes=[ord(x) for x in data]

        if len(bytes)<10:
            not_rom(fname,"too small")
            continue

        copyr_offset=bytes[7]+1
        copyr=get_str(data,copyr_offset)
        if copyr is None or copyr[:3]!="(C)" or bytes[copyr_offset-1]!=0:
            not_rom(fname,"no (C)")
            continue

        title=get_str(data,9)
        if title is None:
            not_rom(fname,"title fail")
            continue

        version_offset=9+len(title)+1
        version=None
        if version_offset!=copyr_offset:
            version=get_str(data,version_offset)
            if version is None:
                not_rom(fname,"version fail")
                continue

        architectures={
            0:"6502 BASIC",
            2:"6502",
            3:"6800",
            8:"Z80",
            9:"32016",
            11:"80186",
            12:"80286",
        }

        flags=bytes[6]
        serv=(flags&0x80)!=0
        lang=(flags&0x40)!=0
        relo=(flags&0x20)!=0
        elec=(flags&0x10)!=0
        arch=flags&0x0F

        if relo:
            relo_addr_offset=copyr_offset+len(copyr)+1
            if relo_addr_offset+5>=len(bytes):
                not_rom(fname,"relo addr fail")
                continue

            relo_addr=((bytes[relo_addr_offset+0]<<0)|
                       (bytes[relo_addr_offset+1]<<8)|
                       (bytes[relo_addr_offset+2]<<16)|
                       (bytes[relo_addr_offset+3]<<24))

        p("File: %s\n"%fname)
        p("      ROM title: %s\n"%title)
        p("      Version: %02X%s\n"%(bytes[8],
                                     "" if version is None else " (%s)"%version))
        p("      Copyright: %s\n"%copyr)
        p("      Flags: %c%c%c%c\n"%("S" if serv else "-",
                                     "L" if lang else "-",
                                     "R" if relo else "-",
                                     "E" if elec else "-"))
        p("      Architecture: %s\n"%(architectures[arch] if arch in architectures else "Unknown"))
        if relo: p("      Relocation address: &%08X\n"%relo_addr)
        p("      SHA1: %s\n"%hashlib.sha1(data).hexdigest())

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="dump BBC ROM image info")

    # parser.add_argument("-t",
    #                     "--tabular",
    #                     action="store_true",
    #                     help="tabular rather than pretty output")

    parser.add_argument("fnames",
                        nargs="*",
                        metavar="FILE",
                        help="file name of ROM image")

    args=sys.argv[1:]

    options=parser.parse_args(args)
    
    main(options)
