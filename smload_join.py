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
    v('    %d (0x%x) bytes\n'%(len(data),len(data)))
    return data

##########################################################################
##########################################################################

def is_rom(data):
    # check ROM flags.
    if (data[6]&0x80)==0: return False
    if (data[6]&0x02)==0: return False

    # check copyright pointer.
    if data[7]+3>=len(data): return False
    if data[data[7]+0]!=0: return False
    if data[data[7]+1]!=ord('('): return False
    if data[data[7]+2]!=ord('C'): return False
    if data[data[7]+3]!=ord(')'): return False

    # check service entry point makes sense.
    if data[3]!=0x4c: return False
    svc=data[4]|data[5]<<8
    if not (svc>=0x8000 and svc<0x8000+len(data)): return False

    # guess it must be OK then
    return True

##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose

    output_rom=load(options.rom)
    if not is_rom(output_rom): fatal('not a ROM: %s'%options.rom)

    # this is doable in principle.
    if (output_rom[6]&0x40)!=0:
        fatal('language ROMs not currently supported')

    rom_offsets=[0]

    for module_path in options.modules:
        module=load(module_path)

        if not is_rom(module): fatal('not a ROM: %s'%module_path)

        # see http://mdfs.net/Software/BBC/Modules/ModWriting - these
        # are the rules for determining whether something is a
        # relocatable module
        if (module[0]!=0 or (module[2]&0x80)==0):
            fatal('not a relocatable module: %s'%module_path)

        #print hex(module[1]),hex(module[2])

        reloc_offset=module[1]|((module[2]&0x7f)<<8)
        if reloc_offset>len(module):
            fatal('bad relocation address')

        v('    relocation offset: 0x%04x\n'%reloc_offset)
      
        reloc=module[reloc_offset:]
        module=module[:reloc_offset]

        v('    %d bytes ROM, %d bytes relocation\n'%(len(module),
                                                     len(reloc)))

        # # check the relocation table roughly makes sense.
        # index=0
        # for i in range(0,reloc_offset):
        #     if (module[i]&0xc0)==0x80: index+=1

        # if index//8>=len(reloc): fatal('relocation table too short')

        # a module can only be relocated to a page-aligned address.
        while len(output_rom)%256!=0: output_rom.append(0)

        rom_offsets.append(len(output_rom))

        
        base_page=0x80+(len(output_rom)>>8)
        reloc_index=0
        
        v('%s: base page=$%02x\n'%(module_path,base_page))

        for offset,byte in enumerate(module):
            if (byte&0xc0)==0x80:
                index=reloc_index>>3
                mask=1<<(reloc_index&7)
                if index>=len(reloc): fatal('relocation data short')
                    
                if (reloc[index]&mask)!=0:
                    old_byte=byte
                    byte=base_page+(byte-0x80)
                    assert byte>=0 and byte<256
                    
                    v('relocate %s + $%04x: $%02x -> $%02x\n'%(module_path,
                                                               offset,
                                                               old_byte,
                                                               byte))

                reloc_index+=1
                    
            output_rom.append(byte)

    # create new service code.
    #
    # Just call each ROM's routine in turn. If a module handle the
    # request, it'll set A=0 on exit, and subsequent modules will just
    # ignore it.
    new_service_offset=len(output_rom)
    for i,rom_offset in enumerate(rom_offsets):
        if i>0: output_rom+=[0xa6,0xf4] # LDX &F4
        assert rom_offset>=0 and rom_offset<=16384

        svc=0x8000+rom_offset+3

        # JSR $xxxx to the actual service routine.
        output_rom.append(0x20)
        output_rom.append(output_rom[rom_offset+4])
        output_rom.append(output_rom[rom_offset+5])
        
    output_rom.append(0x60)     # RTS

    # point first ROM's service entry point at the new servire code.
    new_service_addr=0x8000+new_service_offset
    output_rom[4]=new_service_addr&0xff
    output_rom[5]=(new_service_addr>>8)&0xff

    if len(output_rom)>(8192 if options.eightk else 16384):
        fatal('output ROM is too large: %d bytes'%len(output_rom))

    #
    v('final ROM is %d bytes\n'%len(output_rom))
    if options.output_path is not None:
        with open(options.output_path,'wb') as f:
            f.write("".join([chr(x) for x in output_rom]))
        v('saved: %s\n'%options.output_path)
        

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='merge ROM and relocatable modules into ROM')

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-8',dest='eightk',action='store_true',help='limit output ROM to 8K rather than 16K')
    parser.add_argument('-o',metavar='FILE',dest='output_path',help='save joined ROM to %(metavar)s')
    parser.add_argument('rom',metavar='ROM',help='use %(metavar)s as basis for ROM')
    parser.add_argument('modules',metavar='MODULE',nargs='*',help='relocatable module to add to ROM')

    main(parser.parse_args())
