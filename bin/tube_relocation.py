#!/usr/bin/python3
import sys,os,os.path,argparse,collections

##########################################################################
##########################################################################

g_verbose=False

def pv(x):
    if g_verbose:
        sys.stdout.write(x)
        sys.stdout.flush()

##########################################################################
##########################################################################

def fatal(x):
    sys.stderr.write('FATAL: %s\n'%x)
    sys.exit(1)

##########################################################################
##########################################################################

def load(path):
    try:
        with open(path,'rb') as f:
            data=f.read()
            pv('Loaded: %s (%d bytes)\n'%(path,len(data)))
            return data
    except IOError as e: fatal(e)

##########################################################################
##########################################################################

def save(path,data):
    if path is not None:
        pv('Saving: %s (%d bytes)\n'%(path,len(data)))
        with open(path,'wb') as f: f.write(data)


##########################################################################
##########################################################################

def decode_char(x):
    if x>=32 and x<=126: return chr(x)
    else: return '\\x%02X'%x

##########################################################################
##########################################################################

ROM=collections.namedtuple('ROM','type version_byte title version_str copyright tube_address descriptor_address bitmap_bank bitmap_bank_absolute bitmap_end_address data') 

##########################################################################
##########################################################################

def print_rom(rom,f):
    f.write('ROM header: Type: 0x%02x\n'%(rom.type))
    
    f.write('            Title: %s\n'%rom.title)

    f.write('            Version: 0x%02x'%rom.version_byte)
    if rom.version_str is not None: f.write(' %s'%rom.version_str)
    f.write('\n')

    f.write('            Copyright: %s\n'%rom.copyright)

    if rom.tube_address is not None:
        f.write('            Tube address: 0x%08x\n'%rom.tube_address)

        if rom.descriptor_address is not None:
            f.write('            Tube relocation descriptor address: 0x%04x\n'%rom.descriptor_address)

            f.write('            Tube relocation bitmap bank: ')
            if rom.bitmap_bank_absolute:
                f.write('%d (0x%x)'%(rom.bitmap_bank,rom.bitmap_bank))
            else: f.write('+%d'%(rom.bitmap_bank))
            f.write('\n')

            f.write('            Tube relocation bitmap end: 0x%04x\n'%(rom.bitmap_end_address))

    f.flush()
            
##########################################################################
##########################################################################

def load_rom(path):
    def bad(x): fatal('%s: %s'%(path,x))
    def unterminated(i,what):
        if i>=len(data): bad('unterminated %s'%what)

    data=load(path)
        
    if len(data)<9: bad('too small to be a paged ROM: %d byte(s)'%len(data))

    if len(data)>16384:
        bad('too large to be a paged ROM: %d bytes)'%len(data))

    type_=data[6]&15
    if type_ not in [0,2]:
        bad('not 6502 code type: %d (0x%x)'%(type_,type_))

    i=9
    title=''
    while i<len(data) and data[i]!=0:
        title+=decode_char(data[i])
        i+=1
    unterminated(i,'name')
    i+=1

    version_str=None
    if i!=data[7]:
        version_str=''
        while i<len(data) and data[i]!=0:
            version_str+=decode_char(data[i])
            i+=1
        unterminated(i,'version string')
        i+=1

    i=data[7]
    if data[i:i+4]!=b'\x00(C)': bad('missing copyright string')
    i+=1                        # skip the 0
    copyright=''
    while i<len(data) and data[i]!=0:
        copyright+=decode_char(data[i])
        i+=1
    unterminated(i,'copyright')
    i+=1

    tube_address=None
    descriptor_address=None
    bitmap_bank=None
    bitmap_bank_absolute=None
    bitmap_end_address=None
    if data[6]&0x20:
        tube_address=(data[i+0]<<0|data[i+1]<<8|data[i+2]<<16|data[i+3]<<24)
        if (tube_address&0xffff0000)!=0:
            descriptor_address=tube_address>>16
            tube_address&=0xffff

            if not (descriptor_address>=0x8000 and
                    descriptor_address+4<=0xc000):
                bad_rom('invalid Tube relocation descriptor address: 0x%04x'%descriptor_address)

            i=descriptor_address-0x8000
            bitmap_end_address=data[i+0]<<0|data[i+1]<<8
            bitmap_bank=data[i+2]

            bitmap_bank_absolute=(bitmap_bank&0x80)==0
            bitmap_bank&=0xf

    rom=ROM(type=data[6],
            version_byte=data[8],
            title=title,
            version_str=version_str,
            copyright=copyright,
            tube_address=tube_address,
            descriptor_address=descriptor_address,
            bitmap_bank=bitmap_bank,
            bitmap_bank_absolute=bitmap_bank_absolute,
            bitmap_end_address=bitmap_end_address,
            data=list(data))

    if g_verbose: print_rom(rom,sys.stdout)

    return rom
    
##########################################################################
##########################################################################

def main2(options):
    global g_verbose
    g_verbose=options.verbose
    
    options.fun(options)

##########################################################################
##########################################################################

def info_cmd(options):
    rom=load_rom(options.path)
    print_rom(rom,sys.stdout)

##########################################################################
##########################################################################

def extract_cmd(options):
    def bad_rom(x): fatal('%s: %s'%(options.language_rom_path,x))
    def bad_bitmap(x): fatal('%s: %s'%(options.bitmap_rom_path,x))
    
    rom=load_rom(options.language_rom_path)
    bitmap_rom=load(options.bitmap_rom_path)
    
    if rom.tube_address is None:
        bad_rom('must have a Tube relocation address')
    if rom.descriptor_address is None:
        bad_rom('must have a Tube relocation descriptor address')

    i=rom.bitmap_end_address-0x8000
    if not (bitmap_rom[i-2]==0xc0 and bitmap_rom[i-1]==0xde):
        bad_bitmap('Tube relocation bitmap is missing 0xC0DE')

    bitmap_size=bitmap_rom[i-3]<<8|bitmap_rom[i-4]<<0
    pv('Bitmap size: %d bytes\n'%bitmap_size)

    n=0
    for x in rom.data:
        if x>=0x7f and x<0xc0: n+=1

    expected_bitmap_size=(n+7)//8
    pv('(Expected bitmap size: %d bytes)\n'%expected_bitmap_size)

    bitmap=bitmap_rom[i-4-expected_bitmap_size:i]
    save(options.output_path,bytes(bitmap))

##########################################################################
##########################################################################

def set_cmd(options):
    rom=load_rom(options.rom_path)

    if rom.tube_address is None:
        fatal('%s: must have a Tube relocation address'%options.rom_path)

    if rom.descriptor_address is None:
        fatal('%s: must have a Tube relocation descriptor'%options.descriptor_address)
    
    bitmap=load(options.bitmap_path)
    if not (bitmap[-1]==0xde and bitmap[-2]==0xc0):
        fatal('%s: not a Tube relocation bitmap'%options.bitmap_path)

    if not (options.bank>=0 and options.bank<16):
        fatal('invalid bank: %d'%(options.bank))

    if options.output is None:
        output_bitmap_path=None
        output_bitmap_data=b''
    else:
        output_bitmap_path=options.output[1]
        if os.path.isfile(output_bitmap_path):
            output_bitmap_data=load(output_bitmap_path)
        else: output_bitmap_data=b''

    output_bitmap_data+=bitmap
    if len(output_bitmap_data)>16384:
        fatal('%s: would end up too large: %d bytes'%
              ('(output data)' if output_bitmap_path is None else output_bitmap_path),
              len(output_bitmap_data))

    i=rom.descriptor_address-0x8000
    bitmap_end_address=0x8000+len(output_bitmap_data)
    rom.data[i]=bitmap_end_address&0xff
    rom.data[i+1]=bitmap_end_address>>8
    
    rom.data[i+2]=(options.bank if options.absolute_bank else options.bank|0x80)

    if options.output is not None:
        save(options.output[0],bytes(rom.data))
        save(options.output[1],output_bitmap_data)

##########################################################################
##########################################################################

def unset_cmd(options):
    def bad(x): fatal('%s: %s'%(options.path,x))

    rom=load_rom(options.path)
    if rom.tube_address is None: bad('must have a Tube relocation address')

    if rom.descriptor_address is None:
        bad('must have a Tube relocation descriptor address')

    rom.data[6]&=~0x20

    save(options.output_path,bytes(rom.data))

##########################################################################
##########################################################################

def auto_int(x): return int(x,0)

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.set_defaults(fun=None)

    subparsers=parser.add_subparsers()

    info_parser=subparsers.add_parser('info',help='''show Tube relocation-related info about a ROM''')
    info_parser.add_argument('path',metavar='ROM',help='''load ROM from %(metavar)s''')
    info_parser.set_defaults(fun=info_cmd)

    extract_parser=subparsers.add_parser('extract',help='''extract Tube relocation bitmap''')
    extract_parser.add_argument('-o','--output',dest='output_path',metavar='BITMAP',help='''write Tube relocation bitmap to %(metavar)s''')
    extract_parser.add_argument('language_rom_path',metavar='ROM',help='''read language ROM from %(metavar)s''')
    extract_parser.add_argument('bitmap_rom_path',metavar='BITMAP-ROM',help='''read Tube relocation bitmap from ROM bank data %(metavar)s''')
    extract_parser.set_defaults(fun=extract_cmd)

    set_parser=subparsers.add_parser('set',help='''set Tube relocation bitmap for a ROM''')
    set_parser.add_argument('-o','--output',nargs=2,metavar=('OUTPUT-ROM','OUTPUT-BITMAP-ROM'),help='''write updated ROM to OUTPUT-ROM; append bitmap to OUTPUT-BITMAP-ROM''')
    set_parser.add_argument('-a','--absolute-bank',action='store_true',help='''indicate BANK is absolute rather than relative''')
    set_parser.add_argument('rom_path',metavar='ROM',help='''read ROM from %(metavar)s''')
    set_parser.add_argument('bitmap_path',metavar='BITMAP',help='''load Tube relocation bitmap from %(metavar)s''')
    set_parser.add_argument('bank',metavar='BANK',type=auto_int,help='''specify Tube relocation bitmap bank''')
    set_parser.set_defaults(fun=set_cmd)

    unset_parser=subparsers.add_parser('unset',help='''unset Tube relocation bit in ROM header''')
    unset_parser.add_argument('-o','--output',dest='output_path',metavar='OUTPUT-ROM',help='''write updated ROM to %(metavar)s''')
    unset_parser.add_argument('path',metavar='ROM',help='''read ROM from %(metavar)s''')
    unset_parser.set_defaults(fun=unset_cmd)

    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    main2(options)

##########################################################################
##########################################################################
    
if __name__=='__main__': main(sys.argv[1:])
