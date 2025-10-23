#!/usr/bin/python3
import sys,argparse,collections,fnmatch

##########################################################################
##########################################################################

Symbol=collections.namedtuple('Symbol','name value')

##########################################################################
##########################################################################

def main2(options):
    with open(options.input_path,'rt') as f:
        lines=[line.rstrip() for line in f.readlines()]

    symbols=[]
    for line_index,line in enumerate(lines):
        def warn(msg):
            sys.stderr.write('%s:%d: %s\n'%(options.input_path,
                                            1+line_index,
                                            msg))
            
        # Skip the file/line info.
        separator=': '
        separator_pos=line.find(separator)
        if separator_pos<0:
            warn('missing "%s" separator'%separator)
            continue
        
        parts=line[separator_pos+len(separator):].split()
        if len(parts)<3:
            warn('unrecognised syntax')
            continue

        include=True
        for exclude_glob in options.exclude_globs:
            if fnmatch.fnmatch(parts[0],exclude_glob):
                include=False
                break

        if not include: continue

        if parts[1] not in ['=',':=']:
            warn('unknown operator: %s'%parts[1])
            continue

        if parts[2].startswith('$'):
            # hex value (hopefully)
            try: value=int(parts[2][1:],16)
            except ValueError as exc: warn(str(exc))
        elif parts[2][0].isdigit() or parts[2][0]=='-':
            # decimal value, hopefully
            try: value=int(parts[2],10)
            except ValueError as exc: warn(str(exc))
        elif parts[2] in ['true','false']:
            # boolean - ignore
            pass
        elif parts[2].startswith('"'):
            # string - ignore
            continue
        elif parts[2].startswith('['):
            # list - ignore
            continue
        else:
            warn('unrecognised value: %s'%parts[2][:10])
            continue

        symbols.append(Symbol(name=parts[0],
                              value=value))

    def output(f):
        f.write('[{%s}]'%(','.join(["'%s':%dL"%(symbol.name,
                                                symbol.value)
                                    for symbol in symbols])))

    if options.output_path=='-': output(sys.stdout)
    else:
        with open(options.output_path,'wt') as f: output(f)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-o','--output',dest='output_path',metavar='FILE',help='''write BeebAsm symbols to %(metavar)s. Specify - for stdout''')

    parser.add_argument('--exclude-glob',action='append',dest='exclude_globs',metavar='PATTERN',help='''exclude symbols with names matching %(metavar)s, a glob pattern''')

    parser.add_argument('input_path',metavar='FILE',help='''read 64tass --dump-labels output from %(metavar)s''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
