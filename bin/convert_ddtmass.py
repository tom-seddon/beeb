#!/usr/bin/python3
import sys,os,os.path,argparse,collections

##########################################################################
##########################################################################

# Guesswork:

# .labels are local to their $START...$END block
#
# .'labels are globals
#
# \ introduces a comment
#
# @E refers to current address

##########################################################################
##########################################################################

# TODO: should fix up labels such as "x" (etc.) that would trigger the
# shadow definition of built-in warning

##########################################################################
##########################################################################

# 64tass output properties
CODE_COLUMN=16
COMMENT_COLUMN=32

##########################################################################
##########################################################################

NMOS_MNEMONICS=['ADC','AND','ASL','BCC','BCS','BEQ','BIT','BMI','BNE','BPL','BRK','BVC','BVS','CLC','CLD','CLI','CLV','CMP','CPX','CPY','DEC','DEX','DEY','EOR','INC','INX','INY','JMP','JSR','LDA','LDX','LDY','LSR','NOP','ORA','PHA','PHP','PLA','PLP','ROL','ROR','RTI','RTS','SBC','SEC','SED','SEI','STA','STX','STY','TAX','TAY','TSX','TXA','TXS','TYA']

# CMOS_MNEMONICS=NMOS_MNEMONICS.union(set(['PLX','PLY','PHX','PHY','STZ','TSB','TRB','BRA']))

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose: sys.stderr.write(msg)

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)
    
##########################################################################
##########################################################################

def get_suffix(s,prefix):
    assert isinstance(s,bytes),type(s)
    assert isinstance(prefix,bytes),type(prefix)
    
    if s.startswith(prefix): return s[len(prefix):]
    else: return None

##########################################################################
##########################################################################

def find_bbc_file(including_file_path,include_file_bbc_name):
    root=os.path.split(including_file_path)[0]

    path=os.path.join(root,include_file_bbc_name)
    if os.path.isfile(path): return path

    path=os.path.join(root,'$.%s'%include_file_bbc_name)
    if os.path.isfile(path): return path

    return None
    
##########################################################################
##########################################################################

File=collections.namedtuple('File','path name')
# Line=collections.namedtuple('Line','file number bytes')
Location=collections.namedtuple('Location','file line column')

class Line:
    def __init__(self,file,number,bytes):
        self.file=file
        self.number=number
        self.bytes=bytes

    def get_location_prefix(self):
        return '%s:%d'%(self.file.path,self.number)

def read(input_path,name,lines,indent=''):
    pv('%sReading: %s\n'%(indent,input_path))

    file=File(path=input_path,name=name)

    with open(input_path,'rb') as f: data=f.read()

    if len(data)>0:
        if data[-1]!=13:
            data=bytearray(data)
            data.append(13)

    line_index=0
    line_begin=0
    while line_begin<len(data):
        line_end=data.find(13,line_begin)
        assert line_end!=-1

        line_bytes=data[line_begin:line_end]
        line_number=line_index+1
        line_index+=1

        line_begin=line_end+1

        # handle any directives that need doing immediately.
        sline=line_bytes.strip()
        include_file=get_suffix(sline,b'$INCLUDE ')
        if include_file is not None:
            # doesn't check .inf files. Assumes on-disk naming as per
            # BeebLink, ssd_extract or adf_extract.
            input_path2=find_bbc_file(input_path,include_file.decode('ascii'))
            if input_path2 is None:
                fatal('''%s:%d: can't find $INCLUDE file: %s'''%(input_path,line_no,include_file))

            # this is a bit dumb, because it goes through the while
            # parsing process, even though that's unnecessary.
            #
            # oh well.
            lines.append(Line(file=file,
                              number=line_number,
                              bytes=b'; include_start: '+include_file))
            read(input_path2,include_file.decode('ascii'),lines,indent+'  ')
            lines.append(Line(file=file,
                              number=line_number,
                              bytes=b'; include_end: '+include_file))
            continue

        # split line into parts?
        in_string=False
        stmt_begin=0
        stmt_end=0
        any=False
        while stmt_end<len(line_bytes):
            if line_bytes[stmt_end]==ord('"'):
                in_string=not in_string
                stmt_end+=1
            elif line_bytes[stmt_end]==ord(':') and not in_string:
                lines.append(Line(file=file,
                                  number=line_number,
                                  bytes=line_bytes[stmt_begin:stmt_end]))
                any=True
                stmt_end+=1
                stmt_begin=stmt_end
            else: stmt_end+=1

        if stmt_begin!=stmt_end:
            lines.append(Line(file=file,
                              number=line_number,
                              bytes=line_bytes[stmt_begin:stmt_end]))
        elif not any: lines.append(Line(file=file,
                                        number=line_number,
                                        bytes=line_bytes))

##########################################################################
##########################################################################

def is_alpha_byte(n):
    return (n>=ord('a') and n<=ord('z') or
            n>=ord('A') and n<=ord('Z'))

##########################################################################
##########################################################################

def is_symbol_byte(n):
    return (n>=ord('0') and n<=ord('9') or
            is_alpha_byte(n) or
            n==ord('_'))

##########################################################################
##########################################################################

def fix_up_references(text,old,new,fun):
    if text is None: return None
    
    assert isinstance(text,bytes),type(text)
    assert isinstance(old,bytes),type(old)
    assert isinstance(new,bytes),type(new)
    
    i=0
    in_string=False
    while i<len(text):
        if text[i]==ord('"'):
            in_string=not in_string
            i+=1
        elif ((not in_string) and text[i:i+len(old)]==old):
            i2=i+len(old)

            if i>0 and fun(text[i-1]):
                i=i2
                continue

            if i2<len(text) and fun(text[i2]):
                i=i2
                continue

            text=text[:i]+new+text[i2:]
            i=i+len(new)
        else: i+=1

    return text

def fix_up_operator_references(text,old_oper,new_oper):
    return fix_up_references(text,old_oper,new_oper,is_alpha_byte)

def fix_up_label_references(text,old_label,new_label):
    return fix_up_references(text,
                             old_label.encode('ascii'),
                             new_label.encode('ascii')
                             ,is_symbol_byte)

##########################################################################
##########################################################################

# Split each line into its constituent parts: label, label value,
# code, comment.
def split_lines(lines,lines_by_label):
    # Split each line into its parts.
    for line in lines:
        def fatal_line(msg,i=None):
            prefix='%s:%d'%(line.file.path,line.number)
            if i is not None: prefix+=':%d'%(i+1)
            fatal('%s: %s'%(prefix,msg))
            
        line.label=None              # string
        line.label_value=None        # bytes
        line.code=None               # bytes
        line.comment=None            # string
        line.label_is_global=None
        line.sticky_code=False

        i=0
        l=line.bytes

        def skip_spaces():
            nonlocal i
            while i<len(l) and (l[i]==32 or l[i]==9): i+=1

        skip_spaces()
        
        if i<len(l) and l[i]==ord('.'):
            # Extract label
            line.label=''
            i+=1                # skip '.'
            while i<len(l):
                if (is_symbol_byte(l[i]) or
                    l[i]==ord('_') or
                    l[i]==ord("'")):
                    line.label+=chr(l[i])
                    i+=1
                else: break

            if line.label.startswith("'"):
                line.label=line.label[1:]
                line.label_is_global=True
            else: line.label_is_global=False

            lines_by_label.setdefault(line.label,[]).append(line)
                # Location(file=line.file,
                #          line=line.number,
                #          column=None))

        skip_spaces()

        # Extract code or label value.
        if i<len(l):
            if line.label is not None and l[i]==ord('='):
                i+=1
                while i<len(l) and (l[i]==32 or l[i]==9): i+=1
                is_code=False
            else: is_code=True

            skip_spaces()

            in_string=False
            value_begin=i
            value_end=value_begin
            while value_end<len(l):
                if l[value_end]==ord('"'): in_string=not in_string
                elif l[value_end]==ord('\\') and not in_string:
                    # reached comment
                    break
                elif l[value_end]>=128:
                    if not in_string:
                        fatal_line('bad char: %d'%l[value_end],value_end)
                value_end+=1
                
            if value_end>=len(l) and in_string:
                fatal_line('unterminated string')

            content=l[value_begin:value_end].rstrip()
            if is_code:
                if len(content.strip())==0: content=None
                line.code=content
            else: line.label_value=content
            
            i=value_end

        if i<len(l) and l[i]==ord('\\'):
            # Remainder of line is a comment.
            for j in range(i,len(l)):
                if l[j]>=128: fatal_line('bad char: %d'%l[j],j)
            line.comment=l[i+1:].decode('ascii')

##########################################################################
##########################################################################

# Find duplicated labels. All the labels will be globals in the 64tass
# output, so duplicated local names will need uniquifying.
#
# The result is ugly, but oh well.

LabelRename=collections.namedtuple('LabelRename','new_name file')

def fix_up_duplicated_labels(lines,lines_by_label):
    for label,label_lines in lines_by_label.items():
        if len(label_lines)==1: continue # not duplicated
        
        for i in range(len(label_lines)):
            for j in range(i+1,len(label_lines)):
                if label_lines[i].file is label_lines[j].file:
                    fatal('label duplicated in same file: %s'%label)

        rename_index=0
        for label_line in label_lines:
            if not label_line.label_is_global:
                # rename occurrences of this label in the same file
                label_line.label='%s_%d'%(label_line.label,rename_index)
                rename_index+=1
                for line in lines:
                    if line.file is label_line.file:
                        line.code=fix_up_label_references(line.code,
                                                          label,
                                                          label_line.label)
                        line.label_value=fix_up_label_references(line.label_value,
                                                                 label,
                                                                 label_line.label)

##########################################################################
##########################################################################

# Sort out any non-ASCII chars.
#
# split_lines already checked that such bytes are inside strings, and
# the fixing up assumes they're going to end up as operands to .byte.
def fix_up_non_ascii_chars(lines):
    def fix(text):
        if text is not None:
            assert isinstance(text,bytes),type(text)
            i=0
            while i<len(text):
                if text[i]>=128:
                    snippet=b'",%d,"'%text[i]
                    text=text[:i]+snippet+text[i+1:]
                    i+=len(snippet)
                else: i+=1

        return text
        
    for line in lines:
        line.code=fix(line.code)
        line.label_value=fix(line.label_value)

##########################################################################
##########################################################################

# Make opcodes, accumulator and indexing references lower case.
#
# Use $ as the hex char rather than &.
#
# Replace @E with *.
#
# Replace MOD with % etc.
def fix_up_assembler_oddities(lines):
    mnemonics=[x.encode('ascii') for x in NMOS_MNEMONICS]

    indexing_suffixes=[b',X',b',Y',b',X)']
    
    for line in lines:
        if line.code is not None:
            for mnemonic in mnemonics:
                if line.code.startswith(mnemonic):
                    line.code=(mnemonic.lower()+
                               line.code[len(mnemonic):])
                    break

            for indexing_suffix in indexing_suffixes:
                if line.code.endswith(indexing_suffix):
                    line.code=(line.code[:-len(indexing_suffix)]+
                               indexing_suffix.lower())

            # Could be cleverer.
            if line.code.endswith(b' A'): line.code=line.code[:-2]+b' a'

        def fix_stuff(text):
            if text is not None:
                for i in range(len(text)):
                    if (text[i]==ord('&') and
                        i+1<len(text) and
                        (text[i+1]>=ord('0') and text[i+1]<=ord('9') or
                         text[i+1]>=ord('A') and text[i+1]<=ord('F') or
                         text[i+1]>=ord('a') and text[i+1]<=ord('f'))):
                        text=text[:i]+b'$'+text[i+1:]

                text=fix_up_operator_references(text,b'@E',b'*')
                text=fix_up_operator_references(text,b'MOD',b'%')
                text=fix_up_operator_references(text,b'EOR',b'^')

            return text

        line.code=fix_stuff(line.code)
        line.label_value=fix_stuff(line.label_value)

##########################################################################
##########################################################################

def fix_up_pseudo_ops(lines):
    replacements={
        b'$EQUS':b'.text',
        b'$EQUB':b'.byte',
        b'$EQUW':b'.word',
        b'$EQUD':b'.dword',
    }
    orge=b'$ORGE'
    defm=b'$DEFM'
    
    macro_parameter_names=None
    
    for line in lines:
        def startswith_any(prefixes):
            for prefix in prefixes:
                if line.code.startswith(prefix): return True
            return False

        if line.code is not None:
            if macro_parameter_names is not None:
                for name in macro_parameter_names:
                    line.code=fix_up_label_references(line.code,
                                                      name,
                                                      '(\\%s)'%name)
                
            for old,new in replacements.items():
                if line.code.startswith(old):
                    line.code=new+line.code[len(old):]
                    break

            if line.code==b'$END': line.code=None
            elif line.code==b'$START': line.code=None
            elif line.code.startswith(orge):
                assert line.label is None
                assert line.label_value is None
                line.label='*'
                line.label_value=line.code[len(orge):]
                line.code=None
            elif (startswith_any([b'$ATD',
                                  b'$LIST',
                                  b'$ERROR',
                                  b'$ORGV']) or
                  line.code.startswith(b'*')):
                line.code=b'; '+line.code
            elif startswith_any([b'$IF',b'$ENDIF']):
                sys.stderr.write('%s: WARNING: completely ignoring $IF/$ENDIF directive\n'%line.get_location_prefix())
                line.code=b'; '+line.code
            elif line.code.startswith(defm):
                assert macro_parameter_names is None
                defm_args=line.code[len(defm):].split()
                macro_name=defm_args[0].decode('ascii')
                if macro_name.startswith("'"): macro_name=macro_name[1:]
                macro_parameter_names=[x.decode('ascii') for x in defm_args[1:]]
                assert line.label is None
                line.label=macro_name
                line.sticky_code=True
                line.code=b'.macro '+b' '.join(defm_args[1:])
            elif line.code==b'$ENDM':
                line.code=b'.endmacro'
                macro_parameter_names=None

##########################################################################
##########################################################################

def write_output(lines,f):
    # f.write('''%s.tdef "|",$7f\n'''%(CODE_COLUMN*' '))
    # f.write('''%s.tdef "\\",$5c\n'''%(CODE_COLUMN*' '))
    # f.write('''%s.tdef "~",$7e\n'''%(CODE_COLUMN*' '))
    
    for line in lines:
        text=''

        def flush():
            nonlocal text
            
            f.write('%s\n'%text)
            text=''

        def column(n):
            nonlocal text

            while len(text)<n: text+=' '
        
        if line.label is not None:
            if line.label_value is not None:
                text='%s=%s'%(line.label,line.label_value.decode('ascii'))
            else: text='%s:'%line.label

        if line.code is not None:
            if len(text)>=CODE_COLUMN-1 and not line.sticky_code: flush()
            column(CODE_COLUMN)
            text+=line.code.decode('ascii')

        if line.comment is not None:
            # if 'ELECTRON BASED' in line.comment:
            #     print('%s:%d'%(line.file.path,line.number))
            #     print('  got label=%d; got code=%d'%(line.label is not None,line.code is not None))
            if len(text)>0: column(COMMENT_COLUMN)
            text+='; %s'%line.comment

        flush()

##########################################################################
##########################################################################

def main2(options):
    global g_verbose;g_verbose=options.verbose
    
    lines=[]
    read(options.input_path,None,lines)
    pv('read %d lines\n'%len(lines))

    lines_by_label={}
    split_lines(lines,lines_by_label)

    fix_up_duplicated_labels(lines,lines_by_label)

    fix_up_non_ascii_chars(lines)

    fix_up_assembler_oddities(lines)

    fix_up_pseudo_ops(lines)

    if options.output_path=='-': write_output(lines,sys.stdout)
    elif options.output_path is not None:
        with open(options.output_path,'wt') as f: write_output(lines,f)
    
##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')
    parser.add_argument('-o','--output',dest='output_path',metavar='FILE',help='''write output to %(metavar)s. Specify '-' for stdout''')
    parser.add_argument('input_path',metavar='FILE',help='''read input file from %(metavar)s''')

    main2(parser.parse_args(argv))
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
