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
    def bad(x): fatal('%s : %s'%(path,x))
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

        if (tube_address&0xff)!=0:
            bad('Tube address not page-aligned: 0x%x'%tube_address)
            
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
            data=bytearray(data))

    if g_verbose: print_rom(rom,sys.stdout)

    return rom

##########################################################################
##########################################################################

def load_bitmap(path):
    bitmap=load(path)
    
    if len(bitmap)<4:
        fatal('%s : bitmap file too small: %d bytes'%(options.bitmap_path,len(bitmap)))
    elif len(bitmap)>16384:
        fatal('%s : bitmap file too large: %d bytes'%(options.bitmap_path,len(bitmap)))

    if not (bitmap[-2]==0xc0 and bitmap[-1]==0xde):
        fatal('%s : bitmap missing 0xC0DE trailer'%path)

    bitmap_size=bitmap[-3]*256+bitmap[-4]
    if len(bitmap)!=bitmap_size+4:
        fatal('%s : bitmap file is wrong size. Expected: %d (0x%x)'%(path,bitmap_size+4,bitmap_size+4))

    return bitmap

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
    def bad_rom(x): fatal('%s : %s'%(options.language_rom_path,x))
    def bad_bitmap(x): fatal('%s : %s'%(options.bitmap_rom_path,x))
    
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
    save(options.output_path,bitmap)

##########################################################################
##########################################################################

def relocate_cmd(options):
    rom=load_rom(options.rom_path)

    if (rom.tube_address is None or
        rom.descriptor_address is None):
        fatal('%s : must be relocatable ROM'%(options.rom_path))
    
    bitmap=load_bitmap(options.bitmap_path)

    delta=(rom.tube_address>>8)-0x80

    mask=128
    index=len(bitmap)-5
    relocated=[]
    for i,x in enumerate(rom.data):
        if x>=0x7f and x<0xc0:
            #pv('+0x%04x: 0x%x: bitmap[%d]=0x%02x, mask=0x%02x: relocate=%s\n'%(i,x,index,bitmap[index],mask,(bitmap[index]&mask!=0)))
            if bitmap[index]&mask: x+=delta
            mask>>=1
            if mask==0:
                mask=128
                index-=1
            
        relocated.append(x)

    save(options.output_path,bytes(relocated))

##########################################################################
##########################################################################

def set_cmd(options):
    if (options.bitmap_offset is not None and
        options.bitmap_addr is not None):
        fatal('only one of bitmap offset or bitmap address may be specified')

    rom=load_rom(options.rom_path)

    if rom.tube_address is None:
        fatal('%s : must have a Tube relocation address'%options.rom_path)

    if rom.descriptor_address is None:
        fatal('%s : must have a Tube relocation descriptor'%options.rom-path)
    
    bitmap=load_bitmap(options.bitmap_path)

    if ((options.absolute_bank and not (options.bank>=0 and
                                        options.bank<16)) or
        (not options.absolute_bank and not (options.bank>=-15 and
                                            options.bank<=15))):
        fatal('invalid bank: %d'%(options.bank))

    if options.output is None:
        output_bitmap_path=None
        output_bitmap_data=b''
    else:
        output_bitmap_path=options.output[1]
        if os.path.isfile(output_bitmap_path):
            output_bitmap_data=load(output_bitmap_path)
        else: output_bitmap_data=b''

    if options.bitmap_offset is not None:
        if options.bitmap_offset<0:
            fatal('invalid bitmap offset: %d'%options.bitmap_offset)
        bitmap_offset=options.bitmap_offset
    elif options.bitmap_address is not None:
        if options.bitmap_address<0x8000:
            fatal('invalid bitmap address 0x%04x'%options.bitmap_address)
        bitmap_offset=options.bitmap_address-0x8000
    else:
        bitmap_offset=len(output_bitmap_data)

    # Always account for an extra byte; the relocation data could be
    # in theory up to 3 bits larger (in practice: up to 2 bits) due to
    # the change in descriptor contents.
    bitmap_end_offset=bitmap_offset+1+len(bitmap)
    if bitmap_end_offset>16384:
        name=('(output data)' if output_bitmap_path is None else output_bitmap_path)
        fatal('%s : would end up too large: %d bytes'%(name,
                                                       bitmap_end_offset))

    # Extend bitmap data if necessary.
    if bitmap_end_offset>len(output_bitmap_data):
        output_bitmap_data+=b'\x00'*(bitmap_end_offset-len(output_bitmap_data))

    # bytes is a very annoying type, if you're trying to modify the
    # data.
    output_bitmap_data=bytearray(output_bitmap_data)

    # Record relocate flags. 1 entry per language ROM byte:
    # True/False, indicating whether this byte needs relocating.
    # Ignored for non-relocatable bytes.
    relocate=[False]*len(rom.data)
    mask=128
    index=len(bitmap)-5
    for i,x in enumerate(rom.data):
        if x>=0x7f and x<0xc0:
            relocate[i]=(bitmap[index]&mask)!=0
            mask>>=1
            if mask==0:
                mask=128
                index-=1

    # Adjust relocation bitmap address.
    bitmap_end_address=0x8000+bitmap_end_offset
    i=rom.descriptor_address-0x8000

    rom.data[i+0]=bitmap_end_address&0xff
    rom.data[i+1]=bitmap_end_address>>8
    rom.data[i+2]=options.bank&15
    if not options.absolute_bank: rom.data[i+2]|=0x80

    relocate[i+0]=False
    relocate[i+1]=False
    relocate[i+2]=False

    # Rebuild relocation table
    output_index=bitmap_end_offset
    output_bitmap_data[output_index-1]=0xde
    output_bitmap_data[output_index-2]=0xc0
    output_index-=5
    output_mask=128
    for i,x in enumerate(rom.data):
        if x>=0x7f and x<0xc0:
            if relocate[i]: output_bitmap_data[output_index]|=output_mask
            else: output_bitmap_data[output_index]&=~output_mask
            output_mask>>=1
            if output_mask==0:
                output_mask=128
                output_index-=1
        else: assert not relocate[i]

    assert output_index>=bitmap_offset
    bitmap_size=(bitmap_end_offset-output_index)-4
    output_bitmap_data[bitmap_end_offset-3]=bitmap_size>>8
    output_bitmap_data[bitmap_end_offset-4]=bitmap_size&0xff

    if options.output is not None:
        save(options.output[0],rom.data)
        save(options.output[1],output_bitmap_data)

##########################################################################
##########################################################################

def unset_cmd(options):
    def bad(x): fatal('%s : %s'%(options.path,x))

    rom=load_rom(options.path)
    if rom.tube_address is None: bad('must have a Tube relocation address')

    if rom.descriptor_address is None:
        bad('must have a Tube relocation descriptor address')

    rom.data[6]&=~0x20

    save(options.output_path,rom.data)

##########################################################################
##########################################################################

def create_cmd(options):
    rom=load_rom(options.rom_path)
    if rom.descriptor_address is None:
        # Ensure the output of this is something that the set command
        # can consume. Though in principle you could sort this stuff
        # out yourself, so maybe this check should be optional?
        fatal('%s : must have a Tube relocation address and descriptor'%options.rom_path)

    rom2=load_rom(options.other_rom_path)

    if len(rom.data)!=len(rom2.data): fatal('ROMs are not the same length')

    # Build the bitmap
    num_diffs=0
    expected_delta=None
    bitmap=[]
    num_relocs=0
    for i in range(len(rom.data)):
        if rom.data[i]>=0x7f and rom.data[i]<=0xbf:
            reloc=False
            delta=rom2.data[i]-rom.data[i]
            if delta!=0:
                reloc=True
                if expected_delta is None: expected_delta=delta
                elif delta!=expected_delta:
                    fatal('distance not constant at +%d (+0x%x) (expected %d; got %d)'%(i,i,expected_delta,delta))

            index=num_relocs>>3
            mask=1<<(7-(num_relocs&7))
            if index==len(bitmap): bitmap.append(0)
            if reloc: bitmap[index]|=mask
            num_relocs+=1

    bitmap.reverse()
    bitmap+=[0xc0,0xde]

    pv('%d bitmap bytes (%d relocatable bytes)\n'%(len(bitmap),num_relocs))

    bitmap=bytes(bitmap)
    if options.output_path is not None: save(options.output_path,bitmap)

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
    extract_parser.add_argument('-o','--output',dest='output_path',metavar='OUTPUT-BITMAP',help='''write Tube relocation bitmap to %(metavar)s''')
    extract_parser.add_argument('language_rom_path',metavar='INPUT-ROM',help='''read language ROM from %(metavar)s''')
    extract_parser.add_argument('bitmap_rom_path',metavar='INPUT-BITMAP-ROM',help='''read Tube relocation bitmap from ROM bank data %(metavar)s''')
    extract_parser.set_defaults(fun=extract_cmd)

    relocate_parser=subparsers.add_parser('relocate',help='''relocate ROM (result may be invalid)''')
    relocate_parser.add_argument('-o','--output',dest='output_path',metavar='ILE',help='''write relocated ROM to %(metavar)s''')
    relocate_parser.add_argument('rom_path',metavar='ROM',help='''read ROM from %(metavar)s''')
    relocate_parser.add_argument('bitmap_path',metavar='BITMAP',help='''read bitmap from %(metavar)s''')
    relocate_parser.set_defaults(fun=relocate_cmd)

    set_parser=subparsers.add_parser('set',help='''set Tube relocation bitmap for a ROM''')
    set_parser.add_argument('-o','--output',nargs=2,metavar=('OUTPUT-ROM','OUTPUT-BITMAP-ROM'),help='''write updated ROM to OUTPUT-ROM; write/append bitmap to OUTPUT-BITMAP-ROM''')
    set_parser.add_argument('--absolute-bank',action='store_true',help='''indicate BANK is absolute rather than relative''')
    set_parser.add_argument('--bitmap-address',metavar='ADDR',default=None,type=auto_int,help='''insert bitmap so it will start at address %(metavar)s. WARNING: will add or overwrite bitmap ROM data as required''')
    set_parser.add_argument('--bitmap-offset',metavar='OFFSET',default=None,type=auto_int,help='''insert bitmap so it will start at offset %(metavar)s in bitmap ROM. WARNING: will add or overwrite bitmap ROM data as required''')
    set_parser.add_argument('rom_path',metavar='ROM',help='''read ROM from %(metavar)s''')
    set_parser.add_argument('bitmap_path',metavar='BITMAP',help='''load Tube relocation bitmap from %(metavar)s''')
    set_parser.add_argument('bank',metavar='BANK',type=auto_int,help='''specify Tube relocation bitmap bank''')
    set_parser.set_defaults(fun=set_cmd)

    unset_parser=subparsers.add_parser('unset',help='''unset Tube relocation bit in ROM header''')
    unset_parser.add_argument('-o','--output',dest='output_path',metavar='OUTPUT-ROM',help='''write updated ROM to %(metavar)s''')
    unset_parser.add_argument('path',metavar='ROM',help='''read ROM from %(metavar)s''')
    unset_parser.set_defaults(fun=unset_cmd)

    create_parser=subparsers.add_parser('create',help='''create Tube relocation bitmap''')
    create_parser.add_argument('-o','--output',dest='output_path',metavar='OUTPUT-BITMAP',help='''write bitmap data to %(metavar)s''')
    create_parser.add_argument('rom_path',metavar='INPUT-ROM',help='''ROM assembled to run at $8000''')
    create_parser.add_argument('other_rom_path',metavar='INPUT-ROM-2',help='''ROM assembled to run at some other address''')
    create_parser.set_defaults(fun=create_cmd)

    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    main2(options)

##########################################################################
##########################################################################
    
if __name__=='__main__': main(sys.argv[1:])
