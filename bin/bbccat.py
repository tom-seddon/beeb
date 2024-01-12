#!/usr/bin/python3
import os,sys,argparse

def main2(options):
    for path in options.paths:
        with open(path,'rb') as f: data=f.read()
        line=''
        i=0

        def cr(n):
            nonlocal i
            nonlocal line
            
            i+=n-1
            print(line)
            line=''
        
        while i<len(data):
            # Skip any line ending that could plausibly be appropriate
            # for the BBC Micro: so CR, CR LF or LF CR.

            if data[i:i+2]==b'\r\n' or data[i:i+2]==b'\n\r': cr(2)
            elif data[i]==13: cr(1)
            elif data[i]==127 and options.handle_delete:
                # try to do roughly the right thing
                if len(line)>0: line=line[:-1]
            elif data[i]<32 or data[i]>126: line+='\\x%02X'%data[i]
            else: line+=chr(data[i])
            i+=1

        if line!='': print(line)

def main(argv):
    parser=argparse.ArgumentParser(description='print BBC Micro text file to stdout')
    parser.add_argument('-d','--handle-delete',action='store_true',help='''(try to) handle CHR$127''')
    parser.add_argument('paths',metavar='FILE',nargs='+',help='file(s) to print')

    main2(parser.parse_args(argv))

if __name__=='__main__': main(sys.argv[1:])
