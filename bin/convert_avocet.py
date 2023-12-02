#!/usr/bin/python3
import argparse,sys,collections,re

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    sys.exit(1)

##########################################################################
##########################################################################

TAB=9
SPACE=32
COMMENT_CHAR=ord(';')
LABEL_TERMINATOR=ord(':')
DQUOTE=ord('"')
SQUOTE=ord("'")
SEGMENT_TERMINATOR=ord(':')
OFFSET_TERMINATOR=ord(' ')

DATA_XREF_prefix=b'; DATA XREF: '
CODE_XREF_prefix=b'; CODE XREF: '

# SEGMENT_PREFIX_RE=re.compile('^(?P<segment>[0-9A-Za-z_]+):(?P<addr>[0-9A-Fa-f]+) (?P<rest>.*)$')

class Line:
    def __init__(self,number,segment,offset):
        self._number=number
        self.indented=False
        self._segment=segment
        self._offset=offset
        self.parts=[]
        self.comment=None

    @property
    def offset(self): return self._offset

    @property
    def number(self): return self._number

    def is_empty(self):
        return len(self.parts)==0 and self.comment is None

##########################################################################
##########################################################################
        
def get_lines(data,options):
    bol_idx=0
    line_number=1
    lines=[]

    def fatal_line(message):
        fatal('%s:%d: %s'%(options.input_path,line_number,message))

    # Pass 1 - generate array of Line objects.
    while bol_idx<len(data):
        eol_idx=bol_idx
        while data[eol_idx]!=10 and data[eol_idx]!=13: eol_idx+=1

        # the expandtabs was a late addition - there are some
        # subsequent checks for tabs that are now redundant
        line_data=data[bol_idx:eol_idx].expandtabs()

        segment=''
        ch_idx=0
        while (ch_idx<len(line_data) and
               line_data[ch_idx]!=SEGMENT_TERMINATOR):
            segment+=chr(line_data[ch_idx])
            ch_idx+=1

        if ch_idx>=len(line_data): fatal_line('missing segment prefix')

        ch_idx+=1               # skip ':'

        offset=''
        while (ch_idx<len(line_data) and
               line_data[ch_idx]!=OFFSET_TERMINATOR):
            offset+=chr(line_data[ch_idx])
            ch_idx+=1

        try:
            offset=int(offset,16)
        except ValueError: fatal_line('invalid offset: %s'%offset)

        if ch_idx<len(line_data):
            ch_idx+=1           # skip ' '

        ch_idx+=options.num_opcode_bytes*3

        # split into space-separated parts, plus comment (if any).
        line=Line(line_number,segment,offset)
        lines.append(line)
        in_part=False

        str_char=None
        
        next_is_first_char=True
        for ch_idx in range(ch_idx,len(line_data)):
            is_first_char=next_is_first_char
            next_is_first_char=False
            
            ch=line_data[ch_idx]
            if str_char is not None:
                # in string...
                line.parts[-1]+=chr(ch)
                if ch==str_char: str_char=None
            else:
                if ch==TAB or ch==SPACE:
                    if is_first_char: line.indented=True
                    in_part=False
                elif ch==COMMENT_CHAR:
                    in_part=False
                    line.comment=line_data[ch_idx:]
                    # print('%d: comment=``%s\'\''%(line_number,line.comment))
                    break
                else:
                    if ch<32 or ch>126:
                        fatal('%s:%d:%d: bad char: %d (0x%x)'%(options.input_path,
                                                               line_number,
                                                               ch_idx+1,
                                                               ch,ch))

                    if not in_part:
                        line.parts.append('')
                        in_part=True
                    
                    line.parts[-1]+=chr(ch)

                    if ch==DQUOTE or ch==SQUOTE:
                        str_char=ch
                    elif ch==LABEL_TERMINATOR and len(line.parts)==1:
                        # Handle stuff like "fred:.BYTE blahblah'
                        in_part=False

        if str_char is not None:
            fatal('%s:%d: unterminated string'%(options.input_path,
                                                line_number))

        line_number+=1

        # skip line ending to go to next line
        bol_idx=eol_idx+1
        if (bol_idx<len(data) and
            (data[bol_idx]==10 or data[bol_idx]==13)
            and data[bol_idx]!=data[eol_idx]):
            bol_idx+=1

    return lines

##########################################################################
##########################################################################

def fix_up_mnemonics(lines,options):
    mnemonics=set(['ADC','AND','ASL','BCC','BCS','BEQ','BIT','BMI','BNE','BPL','BRK','BVC','BVS','CLC','CLD','CLI','CLV','CMP','CPX','CPY','DEC','DEX','DEY','EOR','INC','INX','INY','JMP','JSR','LDA','LDX','LDY','LSR','NOP','ORA','PHA','PHP','PLA','PLP','ROL','ROR','RTI','RTS','SBC','SEC','SED','SEI','STA','STX','STY','TAX','TAY','TSX','TXA','TXS','TYA'])
    if options.cmos:
        mnemonics=mnemonics.union(set(['PLX','PLY','PHX','PHY','STZ','TSB','TRB','BRA']))

    def get_fixed_up_part(part):
        if part in mnemonics: return part.lower()
        elif part=='.ds': return '.fill'
        elif part=='.db': return '.byte'
        elif part=='.dw': return '.word'
        elif part=='.fcc': return '.text'
        elif part=='A': return 'a'
        else:
            # hex - 0ffh and so on
            part=re.sub('^0([A-Fa-f][0-9A-Fa-f]*)h','$\\1',part)
            part=re.sub('([^A-Za-z0-9_])0([A-Fa-f][0-9A-Fa-f]*)h','\\1$\\2',part)

            # hex - 91h and the like
            part=re.sub('^([1-9][0-9A-Fa-f]*)h','$\\1',part)
            part=re.sub('([^A-Za-z0-9_])([1-9][0-9A-Fa-f]*)h','\\1$\\2',part)

            # binary - 1b etc.
            part=re.sub('^([01]+)b','%\\1',part)
            part=re.sub('([^A-Za-z0-9_])([01]+)b','\\1%\\2',part)
            
            if part.endswith(',X') or part.endswith(',Y'):
                return part[:-2]+part[-2:].lower()
            else: return part

    for line in lines:
        for i in range(len(line.parts)):
            if i==0 and line.parts[i].endswith(':'):
                # Don't fix up labels!
                pass
            else: line.parts[i]=get_fixed_up_part(line.parts[i])

    # Possibly turn .byte into .char
    for line in lines:
        try:
            i=line.parts.index('.byte')
            for j in range(i+1,len(line.parts)):
                if line.parts[j].startswith('-'):
                    line.parts[i]='.char'
                    break
        except ValueError: pass

    # Guess at left-aligned comments
    for index,line in enumerate(lines):
        if (not line.indented and
            line.comment is None and
            len(line.parts)>0 and
            not (line.parts[0].upper() in mnemonics or
                 line.parts[0].endswith(':'))):
            s=bytes(' '.join(line.parts),'ascii')
            sys.stderr.write('%s:%d: assuming comment: %s\n'%(options.input_path,
                                                            index+1,
                                                            s))
            if line.comment is None: line.comment=s
            else: line.comment+=s
            line.parts=[]
            
    # Transform .org to *=xxx
    for line in lines:
        if (len(line.parts)>0 and
            line.parts[0]=='.org'):
            line.parts=['*','=',line.parts[1]]
            line.indented=False

    # Remove the bogus lines after the .segment directives
    i=0
    while i<len(lines):
        if (len(lines[i].parts)==2 and
            lines[i].parts[0]=='.segment' and
            i+1<len(lines) and
            lines[i+1].parts==[lines[i].parts[1]]):
            del lines[i+1]
        i+=1

    # Turn .segment directives into comments
    for line in lines:
        if (len(line.parts)>0 and
            line.parts[0]=='.segment'):
            line.comment=bytes(' '.join(line.parts),'ascii')
            line.parts=[]
            line.indented=False

##########################################################################
##########################################################################

def startswith_any(thing,prefixes):
    for prefix in prefixes:
        if thing.startswith(prefix): return True
    return False

##########################################################################
##########################################################################

SEPARATOR_STRING=';-------------------------------------------------------------------------'
SEPARATOR_BYTES=bytes(SEPARATOR_STRING,'ascii')

# any fixups that make use of the non-ASCII chars
def fix_up_comments(lines,options):
    uninteresting_comment_prefixes=[
        b'; \310',
        b'; \311',
        b'; \272',
    ]

    separator_prefixes=[
        b'; \304',
        b'; \333',
    ]

    def get_fixed_up_comment(line,options):
        if line.comment is None: return None
        elif ('.BYTE' in line.parts and
            len(line.comment)==3 and
            (line.comment[-1]<32 or line.comment[-1]>=127)):
            # unnecessary non-ASCII char comment
            return None
        elif (len(line.parts)==0 and
              not line.indented and
              startswith_any(line.comment,uninteresting_comment_prefixes)):
            return None
        elif (len(line.parts)==0 and
              not line.indented and
              startswith_any(line.comment,separator_prefixes)):
            return SEPARATOR_BYTES
        else: return line.comment

    for line in lines: line.comment=get_fixed_up_comment(line,options)

##########################################################################
##########################################################################

def convert_comments_to_strings(lines,options):
    for line in lines:
        if line.comment is None: continue

        line.comment=line.comment.replace(b'\t',b' ')

        parts=line.comment.split(b' ')

        # strip out any space-separated sections that include ^X or
        # ^Y. These are CODE XREF or DATA XREF locations, and it
        # simplifies things a bit to remove them here.
        parts=[part for part in parts if 24 not in part and 25 not in part]

        line.comment=b' '.join(parts)

        s=''
        for ch in line.comment:
            if ch>=32 and ch<=126: s+=chr(ch)

        line.comment=s

##########################################################################
##########################################################################

def produce_output(lines,f_out,options):
    opcode_column=16
    comment_column=32

    need_org=True
    last_line_actual_comment_column=None
    for line_idx,line in enumerate(lines):
        actual_comment_column=None

        if len(options.code_regions)>0:
            code=False
            for begin,end in options.code_regions:
                if (line.offset is not None and
                    line.offset>=begin and
                    line.offset<end):
                    code=True
                    break
            if not code and line.offset is not None: need_org=True
        else: code=True

        if not code:
            if (not line.indented and
                len(line.parts)>0 and
                line.parts[0].endswith(':')):
                s='%s=$%x'%(line.parts[0][:-1],line.offset)
            elif line.number is None:
                # blank line
                s=''
            else:
                # simply don't print anything at all in this case.
                s=None
        else:
            s=''
            if need_org:
                f_out.write('*=$%x\n'%line.offset)
                need_org=False
            
            if line.indented: s+=opcode_column*' '

            if len(line.parts)>0:
                if (not line.indented and
                    len(line.parts)>1 and
                    line.parts[0].endswith(':')):
                    s+=line.parts[0]
                    while len(s)<opcode_column: s+=' '
                    s+=' '.join(line.parts[1:])
                else: s+=' '.join(line.parts)
        
        if line.comment is not None:
            if s is None: s=''
            if (line.indented and
                (len(line.parts)>0 or
                 last_line_actual_comment_column is not None)):
                actual_comment_column=last_line_actual_comment_column or comment_column
                while len(s)<actual_comment_column: s+=' '
                actual_comment_column=len(s)

            if not line.comment.startswith(';'): s+='; '
            s+=line.comment

        last_line_actual_comment_column=actual_comment_column
        last_line_was_code=code

        if s is not None:
            f_out.write(s)
            #if line.offset is not None: f_out.write(' ; offset=$%04x'%line.offset)
            #f_out.write(' [[indented=%d actual_comment_column=%s]]'%(line.indented,actual_comment_column))
            f_out.write('\n')

##########################################################################
##########################################################################

def fix_up_comments_2(lines,options):
    uninteresting_comment_prefixes=[
        '; FUNCTION CHUNK AT ',
        '; START OF FUNCTION CHUNK FOR ',
        '; END OF FUNCTION CHUNK FOR ',
        '; Input MD5   :',
        '; File Name   :',
        '; Format      :',
        '; Base Address:',
        '; ; Processor:',
        '; ; Target assembler:',
        '; Segment type: ',
    ]

    uninteresting_comment_parts=[
        '; DATA XREF:',
        '; DATA XREF: ...',
        '; CODE XREF:',
        '; CODE XREF: ...',
    ]

    # Strip out anything uninteresting
    i=0
    while i<len(lines):
        old_comment=lines[i].comment
        if lines[i].comment is not None:
            if startswith_any(lines[i].comment,
                              uninteresting_comment_prefixes):
                lines[i].comment=None
            else:
                uninteresting=False
                for part in uninteresting_comment_parts:
                    if part in lines[i].comment:
                        lines[i].comment=lines[i].comment.replace(part,'')
                        uninteresting=True

                lines[i].comment=lines[i].comment.rstrip()

                if ((lines[i].comment==';' or lines[i].comment=='') and
                    (uninteresting or len(lines[i].parts)==0)):
                    lines[i].comment=None
                elif lines[i].comment in ['...',
                                          ' ...',
                                          '; ...']:
                    lines[i].comment=None

        if old_comment is not None and lines[i].is_empty():
            del lines[i]
        else: i+=1

    # Add .block markup for functions.
    #
    # TODO: this can cause problems due to the nested scopes. Might
    # need a switch for this.
    eof_prefix='; End of function '
    i=0
    while i<len(lines):
        if (lines[i].comment is not None and
            lines[i].comment.startswith(eof_prefix)):
            label=lines[i].comment[len(eof_prefix):]+':'
            j=i
            while (j>=0 and
                   not (len(lines[j].parts)>0 and
                        lines[j].parts[0]==label)):
                j-=1
            if j<0:
                fatal('%s:%d: couldn\'t find label for function: %s'%(options.input_path,1+i,label))

            if options.no_blocks:
                # leave everything in place, including the comments -
                # might want to add .endblock in manually
                pass
            else:
                lines[j].parts.append('.block')
                lines[i].indented=True
                lines[i].parts.append('.endblock')
                lines[i].comment=None
                
        i+=1

##########################################################################
##########################################################################

def tidy_up_empty_lines(lines,options):
    # remove runs of 1+ blank lines.
    i=0
    while i+1<len(lines):
        if lines[i].is_empty() and lines[i+1].is_empty(): del lines[i]
        else: i+=1

    # separators should have blank lines above and below.
    i=1
    while i+1<len(lines):
        if (not lines[i].indented and
            len(lines[i].parts)==0 and
            lines[i].comment==SEPARATOR_STRING):
            if not lines[i-1].is_empty():
                lines.insert(i,Line(None,None,None))
                i+=1
                
            if not lines[i+1].is_empty():
                lines.insert(i+1,Line(None,None,None))
                
            i+=1
        else: i+=1

##########################################################################
##########################################################################

def convert_avocet(options):
    with open(options.input_path,'rb') as f: input_data=f.read()

    # ensure data ends with eol
    if input_data[-1]!=10 and input_data[-1]!=13: input_data.append(13)

    lines=get_lines(input_data,options)

    fix_up_mnemonics(lines,options)

    fix_up_comments(lines,options)

    convert_comments_to_strings(lines,options)

    fix_up_comments_2(lines,options)

    tidy_up_empty_lines(lines,options)

    if options.output_path is None: produce_output(lines,sys.stdout,options)
    else:
        with open(options.output_path,'wt') as f:
            produce_output(lines,f,options)

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('--no-blocks',action='store_true',help='''don't emit .block/.endblock directives''')
    parser.add_argument('--65c02',dest='cmos',action='store_true',help='''support 65c02 mnemonics''')
    parser.add_argument('-o','--output',dest='output_path',metavar='FILE',help='''write output to %(metavar)s''')
    parser.add_argument('input_path',metavar='FILE',help='''read .lst input from %(metavar)s''')
    parser.add_argument('-c','--code',dest='code_regions',default=[],nargs=2,metavar=('BEGIN','END'),type=auto_int,action='append',help='''treat region from BEGIN to END as the code''')
    parser.add_argument('-n',dest='num_opcode_bytes',default=0,type=auto_int,metavar='COUNT',help='''strip %(metavar)s opcode byte(s) from start of each line. Default: %(default)s''')
    convert_avocet(parser.parse_args(argv))

##########################################################################
##########################################################################
    
if __name__=='__main__': main(sys.argv[1:])
