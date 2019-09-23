#!/usr/bin/python
import sys,os,os.path,glob,argparse
import mos_switcher

##########################################################################
##########################################################################

def mos_program(options):
    if options.bank<0 or options.bank>7:
        raise RuntimeError('invalid bank: %d'%options.bank)

    with open(options.path,'rb') as f: data=f.read()
    if len(data)!=131072:
        raise RuntimeError('file not 128K: %s'%options.path)
    
    with mos_switcher.Connection() as s:
        s.verbose=options.verbose
        s.device=options.device
        s.reset()
        s.send('p%dan'%options.bank)
        s.send(data,False)
        last_line=''
        while True:
            line=s.readline()
            if line=='OK': break
            last_line=line
        print last_line

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-D','--device',metavar='DEVICE',help='set device name')
    parser.add_argument('bank',metavar='BANK',type=int,help='bank to program')
    parser.add_argument('path',metavar='FILE',help='file to write')

    mos_program(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
