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

address_value_re=re.compile(r'''^address\((?P<value>.*)\)$''')
numeric_value_re=re.compile(r'''^(?P<ivalue>[0-9]+)|\$(?P<xvalue>[0-9A-Fa-f]+)$''')

##########################################################################
##########################################################################

Label=collections.namedtuple('Label','src_path src_line src_column label_line name operator value')

def get_optional_match_group(m,name):
    try: return m.group(name)
    except IndexError: return None

def load_labels_file_2(path,regex):
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
                        operator=m.group('operator'),
                        value=m.group('value').lstrip())
            if label.name in labels:
                sys.stderr.write(f'''WARNING: duplicate name: {label.name}\n''')
                sys.stderr.write(f'''    {path}:{label.label_line}: {label.name} = {label.value}\n''')

                old_label=labels[label.name]
                sys.stderr.write(f'''    {path}:{old_label.label_line}: {old_label.name} = {old_label.value}\n''')
            else: labels[label.name]=label

    return labels

def load_labels_file(path,dump_labels):
    if dump_labels: return load_labels_file_2(path,dump_labels_line_re)
    else: return load_labels_file_2(path,labels_line_re)

def main2(options):
    if options.dump_labels_output and not options.dump_labels_input:
        fatal(f'''can't produce --dump-labels output without --dump-labels input''')

    if options.update and options.output_path=='-':
        fatal(f'''can't update when output is stdout''')

    input_labels=load_labels_file(options.input_path,
                                  options.dump_labels_input)

    if options.update and options.output_path is not None:
        output_labels=load_labels_file(options.output_path,
                                       options.dump_labels_output)
    else: output_labels={}

    #print(input_labels)
  
    for input_label in input_labels.values():
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
            value_str=input_label.value
            
            m=address_value_re.match(value_str)
            if m is not None: value_str=m.group('value')

            m=numeric_value_re.match(value_str)
            if m is None: continue

            ivalue=m.group('ivalue')
            if ivalue is not None: value=int(ivalue,10)
            else: value=int(m.group('xvalue'),16)
            
            match=False
            for value_range in options.value_ranges:
                if ((value_range[0] is None or value>=value_range[0]) and
                    (value_range[1] is None or value<value_range[1])):
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

                f.write(f'''{label.name}{label.operator}{label.value}\n''')
        
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
    parser.add_argument('--name-pattern',action='append',metavar='PATTERN',dest='name_patterns',help='''include labels with names matching glob pattern %(metavar)s (if not specified, names are not filtered)''')
    parser.add_argument('--value-range',action='append',nargs=2,type=auto_int_or_none,dest='value_ranges',metavar=('BEGIN','END'),help='''include labels with integer values between BEGIN (inclusive) and END (exclusive) (either value may be "None") (if not specified, values are not filtered)''')
    
    parser.add_argument('input_path',metavar='FILE',help='''read 64tass symbols from %(metavar)s''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
