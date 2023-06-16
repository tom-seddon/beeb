#!/usr/bin/python3
from __future__ import print_function
import argparse,sys,os.path,struct

##########################################################################
##########################################################################

def main(options):
    with open(options.input_path,'rb') as f: data=f.read()

    if len(data)<2:
        print('FATAL: too small to be a C64 .PRG',file=sys.stderr)
        sys.exit(1)

    index=0
    load=struct.unpack_from('<H',data,index)[0]
    index+=2
    
    exec=load

    if options.execution_address:
        if len(data)<index+2:
            print('FATAL: too small to have a separate execution address',file=sys.stderr)
            sys.exit(1)
        load+=2                 # easiest this way...

        exec=struct.unpack_from('<H',data,index)[0]
        index+=2

    if options.io:
        load=(load&0xffff)|0xffff0000
        exec=(exec&0xffff)|0xffff0000

    with open(options.output_path+'.inf','wt') as f:
        print('%s %x %x'%(os.path.basename(options.output_path),load,exec),
              file=f)
    
    with open(options.output_path,'wb') as f: f.write(data[index:])

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='convert C64 .PRG to BBC Micro data + .inf files')

    parser.add_argument('--io',action='store_true',help='set top 16 bits of load/exec address to all 1s')

    parser.add_argument('-e','--execution-address',action='store_true',help='discard 2nd word in file and use it as execution address')

    parser.add_argument('input_path',metavar='PRG',help='read C64 .PRG from %(metavar)s')
    parser.add_argument('output_path',metavar='STEM',help='write to %(metavar)s and %(metavar)s.inf')
    #parser.add_argument('bbc_name',metavar='NAME',help='use %(metavar)s as BBC name')
    
    main(parser.parse_args())
