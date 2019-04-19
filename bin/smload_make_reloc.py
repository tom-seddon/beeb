#!/usr/bin/python

# See http://mdfs.net/Software/BBC/Modules/ModWriting

import sys,argparse,os,os.path

##########################################################################
##########################################################################

g_verbose=False

def v(x):
    if g_verbose: sys.stderr.write(x)

##########################################################################
##########################################################################
    
def fatal(msg):
    print>>sys.stderr,'FATAL: %s'%msg
    sys.exit(1)
    
##########################################################################
##########################################################################

def load(path):
    v('Loading: %s\n'%path)
    with open(path,'rb') as f: data=[ord(x) for x in f.read()]
    v('    %d bytes\n'%len(data))
    return data

##########################################################################
##########################################################################

def is_rom(data):
    # check ROM flags
    if (data[6]&0x80)==0: return False
    if (data[6]&0x02)==0: return False

    # check copyright pointer
    if data[7]+3>=len(data): return False
    if data[data[7]!=0]: return False
    if data[data[7]+1!=ord('(')]: return False
    if data[data[7]+2!=ord('C')]: return False
    if data[data[7]+3!=ord(')')]: return False

    # guess it must be OK then
    return True

##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose

    rom80=load(options.rom80)
    rom81=load(options.rom81)

    if len(rom80)!=len(rom81): fatal('ROM files not the same size')

    if not is_rom(rom80): fatal('not a ROM: %s'%options.rom80)
    if not is_rom(rom81): fatal('not a ROM: %s'%options.rom81)

    if (rom80[6]&0x40)!=0: fatal('module can\'t have language entry point')

    # the relocation table address is itself relocated.
    reloc_table_addr=0x8000+len(rom80)
    rom80[0]=0
    rom80[1]=reloc_table_addr&0xff
    rom80[2]=(reloc_table_addr>>8)&0xff

    rom81[0]=0
    rom81[1]=rom80[1]
    rom81[2]=rom80[2]+1

    reloc_bits=[]
    
    good=True
    for i in range(len(rom80)):
        diff=rom81[i]-rom80[i]
        if diff!=0 and diff!=1:
            print>>sys.stderr,'FATAL: $%04x: difference is not 1'%i
            good=False

        if (rom80[i]&0xc0)==0x80:
            # if diff!=0: v('%04x '%(0x8000+i))
            reloc_bits.append(diff)
        
    if not good: fatal('not relocatable')

    while len(reloc_bits)%8!=0: reloc_bits.append(0)

    reloc_bytes=[]
    for i in range(0,len(reloc_bits),8):
        reloc_byte=0
        for j in range(8):
            assert reloc_bits[i+j] in [0,1]
            reloc_byte|=reloc_bits[i+j]<<j
        reloc_bytes.append(reloc_byte)

    v('%d bytes relocation data\n'%len(reloc_bytes))

    reloc_addr=0x8000+len(rom80)

    rom80[0]=0
    rom80[1]=reloc_addr&0xff
    rom80[2]=(reloc_addr>>8)&0xff
    
    rom80+=reloc_bytes
    
    v('%d bytes total\n'%len(rom80))

    if len(rom80)>16384: fatal('relocation data made ROM too large')

    if options.output_path is not None:
        with open(options.output_path,'wb') as f:
            f.write("".join([chr(x) for x in rom80]))

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='make sideways ROM module relocation table')

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-o',metavar='FILE',dest='output_path',help='save relocatable module to %(metavar)s')
    parser.add_argument('rom80',metavar='ROM1',help='ROM assembled for $8000')
    parser.add_argument('rom81',metavar='ROM2',help='ROM assembled for $8100 (not actually usable as a ROM)')

    main(parser.parse_args())
    
