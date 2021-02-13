#!/usr/bin/python
from __future__ import print_function
import argparse,sys,os.path,struct

##########################################################################
##########################################################################

def main(options):
    with open(options.input_path,'rb') as f: data=f.read()

    if len(data)<3:
        print>>sys.stderr,'to small to be a C64 .PRG'
        sys.exit(1)

    
    addr=struct.unpack_from('<H',data)[0]

    if options.io: addr|=0xffff0000

    with open(options.output_path+'.inf','wt') as f:
        print('%s %x %x'%(os.path.basename(options.output_path),addr,addr),
              file=f)
    
    with open(options.output_path,'wb') as f: f.write(data[2:])
    

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='convert C64 .PRG to BBC Micro data + .inf files')

    parser.add_argument('--io',action='store_true',help='set top 16 bits of load/exec address to all 1s')

    parser.add_argument('input_path',metavar='PRG',help='read C64 .PRG from %(metavar)s')
    parser.add_argument('output_path',metavar='STEM',help='write to %(metavar)s and %(metavar)s.inf')
    #parser.add_argument('bbc_name',metavar='NAME',help='use %(metavar)s as BBC name')
    
    main(parser.parse_args())
