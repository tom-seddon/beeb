#!/usr/bin/python
import os,sys,argparse

##########################################################################
##########################################################################

def main(options):
    for file_name in options.file_names:
        with open(file_name,'rb') as f: data=f.read()
        data=data.replace('\r','\n')
        with open(file_name,'wt') as f: f.write(data)

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='convert BBC Micro text file to current system line endings')

    parser.add_argument('file_names',
                        metavar='FILE',
                        nargs='+',
                        help='file(s) to convert')

    main(parser.parse_args(sys.argv[1:]))
    
