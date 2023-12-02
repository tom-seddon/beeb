#!/usr/bin/python3
import os,sys,argparse

def main2(options):
    for path in options.paths:
        with open(path,'rb') as f: data=f.read()
        line=''
        i=0
        while i<len(data):
            # Skip LF in the LF CR line ending
            if data[i]==10 and i<len(data) and data[i+1]==13: i+=1
            
            if data[i]==13:
                print(line)
                line=''
            elif data[i]<32 or data[i]>126: line+='\\x%02X'%data[i]
            else: line+=chr(data[i])
            i+=1

        if line!='': print(line)

def main(argv):
    parser=argparse.ArgumentParser(description='print BBC Micro text file to stdout')
    parser.add_argument('paths',metavar='FILE',nargs='+',help='file(s) to print')

    main2(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
