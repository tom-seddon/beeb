#!/usr/bin/env python
#
# (c) 2007 Matt Godbolt.
#
# Updated 2010 by Tom Seddon: improved support for 6502 BASICs, line
# numbers, tweaked code so it's more usable as a library.
#
# Use however you like, as long as you put credit where credit's due.
# Some information obtained from source code from RISC OS Open.
# v0.01 - first release.  Doesn't deal with GOTO line numbers.

import struct, re, getopt, sys,optparse
from types import *

# Referred to as "ESCFN" tokens in the source, starting at 0x8e.
cfnTokens = [
    'SUM', 'BEAT']
# Referred to as "ESCCOM" tokens in the source, starting at 0x8e.
comTokens = [
    'APPEND', 'AUTO', 'CRUNCH', 'DELET', 'EDIT', 'HELP', 'LIST', 'LOAD',
    'LVAR', 'NEW', 'OLD', 'RENUMBER', 'SAVE', 'TEXTLOAD', 'TEXTSAVE', 'TWIN'
    'TWINO', 'INSTALL']
# Referred to as "ESCSTMT", starting at 0x8e.
stmtTokens= [
    'CASE', 'CIRCLE', 'FILL', 'ORIGIN', 'PSET', 'RECT', 'SWAP', 'WHILE',
    'WAIT', 'MOUSE', 'QUIT', 'SYS', 'INSTALL', 'LIBRARY', 'TINT', 'ELLIPSE',
    'BEATS', 'TEMPO', 'VOICES', 'VOICE', 'STEREO', 'OVERLAY']

# The list of BBC BASIC V tokens:
# Base tokens, starting at 0x7f
tokens = [
    ("<&7F>",'OTHERWISE'),#0x7f
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
    ("AUTO",cfnTokens),#0xc6
    ("DELETE",comTokens),#0xc7
    ("LOAD",stmtTokens),#0xc8
    ("LIST",'WHEN'),#0xc9
    ("NEW",'OF'),#0xca
    ("OLD",'ENDCASE'),#0xcb
    'ELSE',#0xcc
    ("SAVE",'ENDIF'),#0xcd
    ("<&CE>",'ENDWHILE'),#0xce
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


def Detokenise(line,
               basicv):
    line_text=""
    i=0
    tokenize=True
    while i<len(line):
        c=ord(line[i])
        #print line_text
        if tokenize and c>=0x7f:
            token=tokens[c-0x7f]

            # if it's a tuple, pick BASIC 2 or BASIC V part.
            if isinstance(token,tuple):
                if basicv:
                    token=token[1]
                else:
                    token=token[0]
            
            if isinstance(token,str):
                text=token
                i+=1

                # Special case
                if text=="REM":
                    tokenize=False
                
            elif token is None:
                # line number
                b=[ord(x) for x in line[i:i+4]]
                msb=b[3]^((b[1]<<4)&0xFF)
                lsb=b[2]^(((b[1]&0x30)<<2)&0xFF)
                line_number=(lsb<<0)|(msb<<8)
                text=str(line_number)
                
                i+=4
            else:
                # 2-byte token
                i+=1
                sub=ord(line[i])
                text=token[1][sub-0x8e]
                i+=1

            line_text+=text
        else:
            line_text+=line[i]
            i+=1

    return line_text
            
#     """Replace all tokens in the line 'line' with their ASCII equivalent."""
#     # Internal function used as a callback to the regular expression
#     # to replace tokens with their ASCII equivalents.
#     def ReplaceFunc(match):
#         ext, token = match.groups()
#         tokenOrd = ord(token[0])
#         if ext: # An extended opcode, CASE/WHILE/SYS etc
#             if ext == '\xc6':
#                 return cfnTokens[tokenOrd-0x8e]
#             if ext == '\xc7':
#                 return comTokens[tokenOrd-0x8e]
#             if ext == '\xc8':
#                 return stmtTokens[tokenOrd-0x8e]
#             raise Exception, "Bad token"
#         else: # Normal token, plus any extra characters
#             return tokens[tokenOrd-127] + token[1:]

#     # This regular expression is essentially:
#     # (Optional extension token) followed by
#     # (REM token followed by the rest of the line)
#     #     -- this ensures we don't detokenise the REM statement itself
#     # OR
#     # (any token)
#     return re.sub(r'([\xc6-\xc8])?(\xf4.*|[\x7f-\xff])', ReplaceFunc, line)

def ReadLines(data):
    """Returns a list of [line number, tokenised line] from a binary
       BBC BASIC V format file."""
    lines = []
    while True:
        if len(data) < 2:
            raise Exception, "Bad program"
        if data[0] != '\r':
            print `data`
            raise Exception, "Bad program"
        if data[1] == '\xff':
            break
        lineNumber, length = struct.unpack('>hB', data[1:4])
        lineData = data[4:length]
        lines.append([lineNumber, lineData])
        data = data[length:]
    return lines

def Decode(data,
           basicv=False):
    """Decode binary data 'data' and write the result to 'output'."""
    output=[]
    lines = ReadLines(data)
    for lineNumber, line in lines:
        lineData = Detokenise(line,
                              basicv)
        output.append((lineNumber,lineData))
    return output

if __name__ == "__main__":
    parser=optparse.OptionParser(usage="%prog [options] INPUT (OUTPUT)\n\nIf no OUTPUT specified, stdout.")
    parser.add_option("-5",
                      "--basicv",
                      action="store_true",
                      help="if specified, BASIC V rather than 6502 BASIC.",
                      default=False)
    options,args=parser.parse_args()
    if len(args)<1:
        parser.print_help()
        print>>sys.stderr,"FATAL: Must specify input file."
        sys.exit(1)

    if len(args)>=2:
        output = open(args[1], 'w')
    else:
        output=sys.stdout

    input=open(args[0],"rb")
    entireFile=input.read()
    input.close()
    del input

    result=Decode(entireFile,
                  options.basicv)
    for num,text in result:
        print>>output,"%d%s"%(num,text)

    if output is not sys.stdout:
        output.close()
