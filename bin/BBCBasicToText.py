#!/usr/bin/python3
#
# (c) 2007 Matt Godbolt.
#
# Updated 2010 by Tom Seddon: improved support for 6502 BASICs, line
# numbers, tweaked code so it's more usable as a library.
#
# Use however you like, as long as you put credit where credit's due.
# Some information obtained from source code from RISC OS Open.
# v0.01 - first release.  Doesn't deal with GOTO line numbers.

import struct, re, getopt, sys,optparse,collections
from types import *

##########################################################################
##########################################################################

# Referred to as "ESCFN" tokens in the source, starting at 0x8e.
cfnTokens = [
    'SUM', 'BEAT']

##########################################################################
##########################################################################

# Referred to as "ESCCOM" tokens in the source, starting at 0x8e.
comTokens = [
    'APPEND', 'AUTO', 'CRUNCH', 'DELET', 'EDIT', 'HELP', 'LIST', 'LOAD',
    'LVAR', 'NEW', 'OLD', 'RENUMBER', 'SAVE', 'TEXTLOAD', 'TEXTSAVE', 'TWIN'
    'TWINO', 'INSTALL']

##########################################################################
##########################################################################

# Referred to as "ESCSTMT", starting at 0x8e.
stmtTokens= [
    'CASE', 'CIRCLE', 'FILL', 'ORIGIN', 'PSET', 'RECT', 'SWAP', 'WHILE',
    'WAIT', 'MOUSE', 'QUIT', 'SYS', 'INSTALL', 'LIBRARY', 'TINT', 'ELLIPSE',
    'BEATS', 'TEMPO', 'VOICES', 'VOICE', 'STEREO', 'OVERLAY']

##########################################################################
##########################################################################

class SpecialToken:
    def __init__(self,basic2,basic5):
        assert basic2 is not None
        assert basic5 is not None
        self._basic2=basic2
        self._basic5=basic5
        self._basic4=None

    def with_basic4_case(self,basic4):
        self._basic4=basic4
        return self

    @property
    def basic2(self): return self._basic2

    @property
    def basic4(self):
        if self._basic4 is not None: return self._basic4
        else: return self._basic2

    @property
    def basic5(self): return self._basic5

# The list of BBC BASIC V tokens:
# Base tokens, starting at 0x7f
tokens = [
    SpecialToken("\x7f",'OTHERWISE'),#0x7f
    'AND',#0x80
    'DIV',#0x81
    'EOR',#0x82
    'MOD',#0x83
    'OR',#0x84
    'ERROR',#0x85
    'LINE',#0x86
    'OFF',#0x87
    'STEP',#0x88
    'SPC',#0x89
    'TAB(',#0x8a
    'ELSE',#0x8b
    'THEN',#0x8c
    None,#0x8d (line number)
    'OPENIN',#0x8e
    'PTR',#0x8f
    'PAGE',#0x90
    'TIME',#0x91
    'LOMEM',#0x92
    'HIMEM',#0x93
    'ABS',#0x94
    'ACS',#0x95
    'ADVAL',#0x96
    'ASC',#0x97
    'ASN',#0x98
    'ATN',#0x99
    'BGET',#0x9a
    'COS',#0x9b
    'COUNT',#0x9c
    'DEG',#0x9d
    'ERL',#0x9e
    'ERR',#0x9f
    'EVAL',#0xa0
    'EXP',#0xa1
    'EXT',#0xa2
    'FALSE',#0xa3
    'FN',#0xa4
    'GET',#0xa5
    'INKEY',#0xa6
    'INSTR(',#0xa7
    'INT',#0xa8
    'LEN',#0xa9
    'LN',#0xaa
    'LOG',#0xab
    'NOT',#0xac
    'OPENUP',#0xad
    'OPENOUT',#0xae
    'PI',#0xaf
    'POINT(',#0xb0
    'POS',#0xb1
    'RAD',#0xb2
    'RND',#0xb3
    'SGN',#0xb4
    'SIN',#0xb5
    'SQR',#0xb6
    'TAN',#0xb7
    'TO',#0xb8
    'TRUE',#0xb9
    'USR',#0xba
    'VAL',#0xbb
    'VPOS',#0xbc
    'CHR$',#0xbd
    'GET$',#0xbe
    'INKEY$',#0xbf
    'LEFT$(',#0xc0
    'MID$(',#0xc1
    'RIGHT$(',#0xc2
    'STR$',#0xc3
    'STRING$(',#0xc4
    'EOF',#0xc5
    SpecialToken("AUTO",cfnTokens),#0xc6
    SpecialToken("DELETE",comTokens),#0xc7
    SpecialToken("LOAD",stmtTokens),#0xc8
    SpecialToken("LIST",'WHEN'),#0xc9
    SpecialToken("NEW",'OF'),#0xca
    SpecialToken("OLD",'ENDCASE'),#0xcb
    SpecialToken('RENUMBER','ELSE'),#0xcc
    SpecialToken("SAVE",'ENDIF'),#0xcd
    SpecialToken("",'ENDWHILE').with_basic4_case('EDIT'),#0xce
    'PTR',#0xcf
    'PAGE',#0xd0
    'TIME',#0xd1
    'LOMEM',#0xd2
    'HIMEM',#0xd3
    'SOUND',#0xd4
    'BPUT',#0xd5
    'CALL',#0xd6
    'CHAIN',#0xd7
    'CLEAR',#0xd8
    'CLOSE',#0xd9
    'CLG',#0xda
    'CLS',#0xdb
    'DATA',#0xdc
    'DEF',#0xdd
    'DIM',#0xde
    'DRAW',#0xdf
    'END',#0xe0
    'ENDPROC',#0xe1
    'ENVELOPE',#0xe2
    'FOR',#0xe3
    'GOSUB',#0xe4
    'GOTO',#0xe5
    'GCOL',#0xe6
    'IF',#0xe7
    'INPUT',#0xe8
    'LET',#0xe9
    'LOCAL',#0xea
    'MODE',#0xeb
    'MOVE',#0xec
    'NEXT',#0xed
    'ON',#0xee
    'VDU',#0xef
    'PLOT',#0xf0
    'PRINT',#0xf1
    'PROC',#0xf2
    'READ',#0xf3
    'REM',#0xf4
    'REPEAT',#0xf5
    'REPORT',#0xf6
    'RESTORE',#0xf7
    'RETURN',#0xf8
    'RUN',#0xf9
    'STOP',#0xfa
    'COLOUR',#0xfb
    'TRACE',#0xfc
    'UNTIL',#0xfd
    'WIDTH',#0xfe
    'OSCLI',#0xff
]

##########################################################################
##########################################################################

class Program:
    def __init__(self):
        self.lines=[]
        self.labels={}
        self._next_label=0

    def add_line(self,num,text):
        self.lines.append((num,text))

    def add_label(self,line):
        if line not in self.labels:
            self.labels[line]=self._next_label
            self._next_label+=1

##########################################################################
##########################################################################

def Detokenise(line,add_labels,program,options):
    line_text=""
    i=0
    tokenize=True
    rem=False
    while i<len(line):
        c=line[i]
        #print line_text
        if tokenize and c>=0x7f:
            token=tokens[c-0x7f]

            # if it's a tuple, pick BASIC 2 or BASIC V part.
            if isinstance(token,SpecialToken):
                if options.basicv: token=token.basic5
                elif options.basic2: token=token.basic2
                else: token=token.basic4
            
            if isinstance(token,str):
                text=token
                i+=1

                # Special case
                if not options.basic2 and text=="REM":
                    tokenize=False
                    rem=True
            elif token is None:
                # line number
                msb=line[i+3]^((line[i+1]<<4)&0xFF)
                lsb=line[i+2]^(((line[i+1]&0x30)<<2)&0xFF)
                line_number=(lsb<<0)|(msb<<8)
                if add_labels:
                    program.add_label(line_number)
                else:
                    if line_number in program.labels:
                        text='@%04d'%program.labels[line_number]
                    else: text=str(line_number)
                                 
                i+=4
            else:
                # 2-byte token
                i+=1
                sub=line[i]
                text=token[sub-0x8e]
                i+=1

            line_text+=text
        else:
            if c==ord('"'):
                if rem:
                    # do nothing
                    pass
                else: tokenize=not tokenize
            if (c<32 or c>=128) and not options.codes: line_text+=' '
            else: line_text+=chr(line[i])
            i+=1

    return line_text
            
##########################################################################
##########################################################################

def ReadLines(data,options):
    """Returns a list of [line number, tokenised line] from a binary
       BBC BASIC V format file."""
    lines = []
    i=0
    while True:
        if i+2>len(data): raise Exception("Bad program")
        if data[i]!=13: raise Exception("Bad program")
        if data[i+1]==255: break

        lineNumber=data[i+1]*256+data[i+2]
        length=data[i+3]
        # lineNumber, length = struct.unpack('>HB', data[i+1:i+4])
        lineData = data[i+4:i+length]
        if not options.basic2 and len(lineData)==0:
            # BASIC IV simply skips empty lines when listing! They're
            # still there, though. You can see them when listing in
            # BASIC II.
            pass
        else: lines.append([lineNumber, lineData])
        i+=length
        #data = data[length:]
    return lines

##########################################################################
##########################################################################

def DecodeProgram(data,options):
    program=Program()

    lines=ReadLines(data,options)

    if not options.line_numbers:
        for num,line in lines:
            Detokenise(line,True,program,options)

    for num,line in lines:
        text=Detokenise(line,False,program,options)
        program.add_line(num,text)

    return program

##########################################################################
##########################################################################

def main(argv):
    parser=optparse.OptionParser(usage="%prog [options] INPUT (OUTPUT)\n\n If no INPUT specified, or INPUT is -, read from stdin. If no OUTPUT specified, print output to stdout.")
    parser.add_option('-2',
                      '--basic2',
                      action='store_true',
                      help='list same as 6502 BASIC II rather than 6502 BASIC IV',
                      default=False)
    parser.add_option("-5",
                      "--basicv",
                      action="store_true",
                      help="interpret as BASIC V rather than 6502 BASIC.",
                      default=False)
    parser.add_option("-c",
                      "--cr",
                      action="store_true",
                      help="separate lines with ASCII 13 (suitable for *EXEC)")
    parser.add_option("--codes",
                      action="store_true",
                      help="pass though control codes")
    parser.add_option('-n',
                      action='store_false',
                      default=True,
                      dest='line_numbers',
                      help="print @ labels, not line numbers (hack for diffs)")
                      
    options,args=parser.parse_args(argv)
    # if len(args)<1:
    #     parser.print_help()
    #     print>>sys.stderr,"FATAL: Must specify input file."
    #     sys.exit(1)

    if len(args)>=1 and args[0]!="-":
        with open(args[0],"rb") as f: entireFile=f.read()
    else: entireFile=sys.stdin.buffer.read()

    program=DecodeProgram(entireFile,options)

    if options.codes:
        if len(args)>=2: output=open(args[1],'wb')
        else: raise Exception('can\'t output codes to stdout')
    else:
        if len(args)>=2: output=open(args[1],'wt')
        else: output=sys.stdout
        
    cr=chr(13) if options.cr else "\n"

    def write(str):
        if options.codes: output.write(str.encode('latin_1'))
        else: output.write(str)
    
    for num,text in program.lines:
        if num in program.labels:
            write('@%04d:%s'%(program.labels[num],cr))

        if options.line_numbers: write('%5d'%num)

        write('%s%s'%(text,cr))

    if output is not sys.stdout: output.close()

if __name__ == "__main__":
    main(sys.argv[1:])
