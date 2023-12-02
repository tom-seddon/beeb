#!/usr/bin/python3
import os,sys,argparse

##########################################################################
##########################################################################

def main(options):
    for file_name in options.file_names:
        with open(file_name,'rt') as f: data=f.read()
        data=data.replace('\n','\r').encode('latin_1')
        with open(file_name,'wb') as f: f.write(data)

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='convert text file to BBC Micro line endings')

    parser.add_argument('file_names',
                        metavar='FILE',
                        nargs='+',
                        help='file(s) to convert')

    main(parser.parse_args(sys.argv[1:]))
    
