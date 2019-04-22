#!/usr/bin/python
import argparse,sys,os.path

##########################################################################
##########################################################################

def main(options):
    with open(options.input_path,'rb') as f: data=f.read()

    if len(data)<3:
        print>>sys.stderr,'to small to be a C64 .PRG'
        sys.exit(1)

    addr=ord(data[0])|ord(data[1])<<8

    with open(options.output_path+'.inf','wt') as f:
        print>>f,'%s %x %x'%(os.path.basename(options.output_path),addr,addr)
    
    with open(options.output_path,'wb') as f: f.write(data[2:])
    

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='convert C64 .PRG to BBC Micro data + .inf files')

    parser.add_argument('input_path',metavar='PRG',help='read C64 .PRG from %(metavar)s')
    parser.add_argument('output_path',metavar='STEM',help='write to %(metavar)s and %(metavar)s.inf')
    #parser.add_argument('bbc_name',metavar='NAME',help='use %(metavar)s as BBC name')
    
    main(parser.parse_args())
