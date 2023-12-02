#!/usr/bin/python3
import os,argparse,sys,hashlib,collections

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

# Python 3's unicode_escape isn't quite the right thing...
g_chars=[]
for i in range(256):
    s=None
    if i==ord('\r'): s='\\r'
    elif i==ord('\n'): s='\\n'
    elif i==ord('\t'): s='\\t'
    elif i>=32 and i<127: s=chr(i)
    else: s='\\x%02x'%i

    assert s is not None
    g_chars.append(s)

def encode(x):
    result=''.join([g_chars[c] for c in x])
    return result

def get_str(data,offset):
    result=''
    i=offset
    while i<len(data) and data[i]!=0:
        i+=1

    if i>=len(data): return None
    else: return encode(data[offset:i])

def not_rom(fname,reason): warn("Not a ROM (%s): %s"%(reason,fname))

def get_maybe_8k_rom(data):
    if len(data)==16384 and data[:8192]==data[8192:]: return data[:8192]
    else: return data

ROMDBRow=collections.namedtuple('ROMDBRow','data sha1 roms')
ROM=collections.namedtuple('ROM','path file_size')

class ROMDB:
    def __init__(self):
        self._rows_by_sha1={}
        self._sha1s_in_order=[]
        self._num_roms_added=0

    @property
    def num_unique_roms(self): return len(self._sha1s_in_order)

    @property
    def num_roms_added(self): return self._num_roms_added

    def add(self,path):
        try:
            with open(path,'rb') as f: data=f.read(16385)
            if len(data)<=16384:
                data=get_maybe_8k_rom(data)
                file_size=len(data)
                sha1=hashlib.sha1(data).hexdigest()
                if sha1 not in self._rows_by_sha1:
                    self._sha1s_in_order.append(sha1)
                    self._rows_by_sha1[sha1]=ROMDBRow(data=data,
                                                      sha1=sha1,
                                                      roms=[])

                self._rows_by_sha1[sha1].roms.append(ROM(path=path,
                                                         file_size=file_size))
                self._num_roms_added+=1
        except (IOError) as e: sys.stderr.write('WARNING: %s: %s\n'%(e,path))

    def is_sha1_known(self,sha1): return sha1 in self._rows_by_sha1

    def db_rows(self):
        for sha1 in self._sha1s_in_order: yield self._rows_by_sha1[sha1]

def main(options):
    if options.org:
        header_prefix='* '
        item_prefix='- '
    else:
        header_prefix=''
        item_prefix='    '
    
    known_roms=ROMDB()
    if len(options.rom_paths)>0:
        sys.stderr.write('Scanning ROM paths...\n')
        for rom_path in options.rom_paths:
            for folder_path,folder_names,file_names in os.walk(rom_path):
                for file_name in file_names:
                    file_path=os.path.join(folder_path,file_name)
                    known_roms.add(file_path)

        sys.stderr.write('Search paths: %d/%d unique\n'%(known_roms.num_unique_roms,known_roms.num_roms_added))

    given_roms=ROMDB()
    for fname in options.fnames: given_roms.add(fname)
    sys.stderr.write('ROMs specified: %d/%d unique\n'%(given_roms.num_unique_roms,given_roms.num_roms_added))

    for row in given_roms.db_rows():
        if options.unknown_only: dump=not known_roms.is_sha1_known(row.sha1)
        elif options.known_only: dump=known_roms.is_sha1_known(row.sha1)
        else: dump=True

        if dump:
            p(header_prefix+'File(s): %s\n'%('; '.join([rom.path for rom in row.roms])))
            
            if len(row.data)<10:
                not_rom(fname,"too small")
                continue
        
            copyr_offset=row.data[7]+1
            copyr=get_str(row.data,copyr_offset)
            if copyr is None or copyr[:3]!="(C)" or row.data[copyr_offset-1]!=0:
                not_rom(fname,"no (C)")
                continue

            title=get_str(row.data,9)
            if title is None:
                not_rom(fname,"title fail")
                continue

            version_offset=9+len(title)+1
            version=None
            if version_offset!=copyr_offset:
                version=get_str(row.data,version_offset)
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

            flags=row.data[6]
            serv=(flags&0x80)!=0
            lang=(flags&0x40)!=0
            relo=(flags&0x20)!=0
            elec=(flags&0x10)!=0
            arch=flags&0x0F

            if relo:
                relo_addr_offset=copyr_offset+len(copyr)+1
                if relo_addr_offset+5>=len(row.data):
                    not_rom(fname,"relo addr fail")
                    continue

                relo_addr=((row.data[relo_addr_offset+0]<<0)|
                           (row.data[relo_addr_offset+1]<<8)|
                           (row.data[relo_addr_offset+2]<<16)|
                           (row.data[relo_addr_offset+3]<<24))
                
            p(item_prefix+"SHA1: %s\n"%hashlib.sha1(row.data).hexdigest())

            p(item_prefix+"Size: %d"%len(row.data))
            for rom in row.roms:
                if rom.file_size!=len(row.data):
                    p(" (some files differ)")
                    break
            p("\n")

            p(item_prefix+"ROM title: %s\n"%title)

            p(item_prefix+"Version: %02X%s\n"%(row.data[8],
                                         "" if version is None else " (%s)"%version))

            p(item_prefix+"Copyright: %s\n"%copyr)

            p(item_prefix+"Flags: %c%c%c%c\n"%("S" if serv else "-",
                                         "L" if lang else "-",
                                         "R" if relo else "-",
                                         "E" if elec else "-"))

            p(item_prefix+"Architecture: %s\n"%(architectures[arch] if arch in architectures else "Unknown"))

            if relo: p(item_prefix+"Relocation address: &%08X\n"%relo_addr)

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="dump BBC ROM image info")

    parser.add_argument('--path',
                        dest='rom_paths',
                        action='append',
                        default=[],
                        metavar='PATH',
                        help='''path(s) to find more ROM images to scan for duplicates''')

    parser.add_argument('--known-only',
                        action='store_true',
                        help='''only show ROMs found elsewhere on the ROM paths''')
    
    parser.add_argument('--unknown-only',
                        action='store_true',
                        help='''only show ROMs not found elsewhere on the ROM paths''')

    parser.add_argument('--org',
                        action='store_true',
                        help='''output in org-mode format''')

    parser.add_argument("fnames",
                        nargs="*",
                        metavar="FILE",
                        help="file name of ROM image")

    args=sys.argv[1:]

    options=parser.parse_args(args)
    
    main(options)
