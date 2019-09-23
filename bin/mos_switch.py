#!/usr/bin/python
import sys,os,os.path,glob,argparse
import mos_switcher

##########################################################################
##########################################################################

def mos_switch(options):
    if options.bank<0 or options.bank>7:
        raise RuntimeError('invalid bank: %d'%options.bank)
    
    with mos_switcher.Connection() as s:
        s.verbose=options.verbose
        s.device=options.device
        s.reset()
        s.send('w%d'%options.bank)
        while True:
            line=s.readline()
            if line=='OK': break
            print line

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    parser.add_argument('-D','--device',metavar='DEVICE',help='set device name')
    parser.add_argument('bank',metavar='BANK',type=int,help='bank to select')

    mos_switch(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
