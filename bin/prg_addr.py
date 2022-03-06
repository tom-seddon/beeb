#!/usr/bin/python3
import argparse,sys

def prg_addr(options):
    with open(options.path,'rb') as f: header=f.read(2)
    if len(header)<2:
        print('FATAL: not a C64 prg file: %s'%options.path,file=sys.stderr)
        sys.exit(1)

    addr=header[0]<<0|header[1]<<8
    if options.io: addr|=0xffff0000

    if options.c_style: print('0x%x'%addr)
    else: print('%X'%addr)

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-c','--c-style',action='store_true',help='print address with C-style syntax')
    parser.add_argument('--io',action='store_true',help='set top 16 bits')
    parser.add_argument('path',metavar='FILE',help='read C64 prg from %(metavar)s')

    prg_addr(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
