#!/usr/bin/python3
import sys,os,os.path,argparse,re,collections,fnmatch

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write(f'''FATAL: {msg}\n''')
    sys.exit(1)

##########################################################################
##########################################################################

labels_line_re=re.compile(r'''^(?P<name>[^ ]*)\s*(?P<operator>=|:=)\s*(?P<value>.*)$''')
dump_labels_line_re=re.compile(r'''^(?P<path>.*):(?P<line>[0-9]+):(?P<column>[0-9]+): (?P<name>.*)(?P<operator>=|:=)(?P<value>.*)$''')
vice_labels_line_re=re.compile(r'''^al\s+(?P<value>[0-9A-Fa-f]+)\s+\.(?P<name>.*)$''')

address_value_re=re.compile(r'''^address\((?P<value>.*)\)$''')
numeric_value_re=re.compile(r'''^(?P<ivalue>[0-9]+)|\$(?P<xvalue>[0-9A-Fa-f]+)$''')

##########################################################################
##########################################################################

class Label:
    def __init__(self,src_path,src_line,src_column,label_line,name,operator,value):
        self.src_path=src_path
        self.src_line=src_line
        self.src_column=src_column
        self.label_line=label_line
        self.name=name
        self.operator=operator
        self.value=value

def load_labels(path,regex):
    def get_optional_match_group(m,name):
        try: return m.group(name)
        except IndexError: return None

    labels={}
    with open(path,'rt') as f:
        for line_index,line in enumerate(f.readlines()):
            m=regex.match(line)
            if m is None:
                sys.stderr.write(f'''{path}:{line_index+1}: syntax error\n''')
                fatal(f'''syntax error''')

            src_line=get_optional_match_group(m,'line')
            src_column=get_optional_match_group(m,'column')

            label=Label(src_path=get_optional_match_group(m,'path'),
                        src_line=src_line and int(src_line),
                        src_column=src_column and int(src_column),
                        label_line=line_index+1,
                        name=m.group('name').strip(),
                        operator=get_optional_match_group(m,'operator'),
                        value=m.group('value').lstrip())
            
            if label.name in labels:
                sys.stderr.write(f'''WARNING: duplicate name: {label.name}\n''')
                sys.stderr.write(f'''    {path}:{label.label_line}: {label.name} = {repr(label.value)}\n''')

                old_label=labels[label.name]
                sys.stderr.write(f'''    {path}:{old_label.label_line}: {old_label.name} = {old_label.value}\n''')
            else: labels[label.name]=label

    return labels

##########################################################################
##########################################################################

def fix_up_64tass_labels(labels):
    for name,label in labels.items():
        value_str=label.value

        # remove address()
        m=address_value_re.match(value_str)
        if m is not None: value_str=m.group('value')

        # convert 64tass syntax numbers
        m=numeric_value_re.match(value_str)
        if m is None: continue  # taken if not a number

        ivalue=m.group('ivalue')
        if ivalue is not None: label.value=int(ivalue,10)
        else: label.value=int(m.group('xvalue'),16)

def load_64tass_dump_labels_file(path):
    labels=load_labels(path,dump_labels_line_re)
    fix_up_64tass_labels(labels)
    return labels

def load_64tass_labels_file(path):
    labels=load_labels(path,labels_line_re)
    fix_up_64tass_labels(labels)
    return labels

##########################################################################
##########################################################################

def load_vice_labels_file(path):
    temp_labels=load_labels(path,vice_labels_line_re)

    labels={}
    for label in temp_labels.values():
        # Convert the VICE naming syntax back to 64tass style.
        label.name=label.name.replace(':','.')

        # VICE label values are always numbers in hex
        assert isinstance(label.value,str)
        label.value=int(label.value,16)

        assert label.name not in labels
        labels[label.name]=label

    return labels
    
##########################################################################
##########################################################################

def main2(options):
    if options.dump_labels_output and not options.dump_labels_input:
        fatal(f'''can't produce --dump-labels output without --dump-labels input''')

    if options.dump_labels_input and options.vice_labels_input:
        fatal(f'''--XXX-labels-input options are mutually exclusive''')

    if options.update and options.output_path=='-':
        fatal(f'''can't update when output is stdout''')

    if options.vice_labels_input:
        input_labels=load_vice_labels_file(options.input_path)
    elif options.dump_labels_input:
        input_labels=load_64tass_dump_labels_file(options.input_path)
    else:
        input_labels=load_64tass_labels_file(options.input_path)

    if options.update and options.output_path is not None:
        if options.dump_labels_output:
            output_labels=load_64tass_dump_labels_file(options.output_path)
        else:
            output_labels=load_64tass_labels_file(options.output_path)
    else: output_labels={}

    #print(input_labels)
  
    for input_label in input_labels.values():
        # for now, exclude any that aren't numbers.
        if not isinstance(input_label.value,int): continue

        # filter by name
        if options.name_patterns is not None:
            match=False
            for name_pattern in options.name_patterns:
                if fnmatch.fnmatch(input_label.name,name_pattern):
                    match=True
                    break

            if not match: continue

        # filter by value
        if options.value_ranges is not None:
            match=False
            if isinstance(input_label.value,int):
                for value_range in options.value_ranges:
                    if ((value_range[0] is None or
                         input_label.value>=value_range[0]) and
                        (value_range[1] is None or
                         input_label.value<value_range[1])):
                        match=True
                        break

            if not match: continue

        # merge with output.
        output_labels[input_label.name]=input_label

    if options.output_path is not None:
        def save_output(f):
            for label in output_labels.values():
                if options.dump_labels_output:
                    f.write(f'''{label.src_path}:{label.src_line}:{label.src_column}: ''')

                f.write(f'''{label.name}{label.operator or '='}${hex(label.value)[2:]}\n''')
        
        if options.output_path=='-': save_output(sys.stdout)
        else:
            with open(options.output_path,'wt') as f: save_output(f)
    
##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    def auto_int(x): return int(x,0)
    
    def auto_int_or_none(x):
        if x=='None': return None
        else: return auto_int(x)

    parser.add_argument('-o','--output',dest='output_path',metavar='FILE',help='''write output to %(metavar)s (specify - for stdout)''')
    parser.add_argument('--update',action='store_true',help='''update output file rather than recreating it''')
    parser.add_argument('--dump-labels-output',action='store_true',help='''produce output in --dump-labels format (must also specify --dump-labels-input)''')
    parser.add_argument('--dump-labels-input',action='store_true',help='''input file is in --dump-labels format''')
    parser.add_argument('--vice-labels-input',action='store_true',help='''input file is in --vice-labels format''')
    parser.add_argument('--name-pattern',action='append',metavar='PATTERN',dest='name_patterns',help='''include labels with names matching glob pattern %(metavar)s (if not specified, names are not filtered)''')
    parser.add_argument('--value-range',action='append',nargs=2,type=auto_int_or_none,dest='value_ranges',metavar=('BEGIN','END'),help='''include labels with integer values between BEGIN (inclusive) and END (exclusive) (either value may be "None") (if not specified, values are not filtered)''')
    
    parser.add_argument('input_path',metavar='FILE',help='''read 64tass symbols from %(metavar)s''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
