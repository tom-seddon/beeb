#!env python
import argparse,os,os.path,sys,struct
emacs=os.getenv("EMACS") is not None

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")
    
    if emacs: raise RuntimeError
    else: sys.exit(1)

##########################################################################
##########################################################################
    
g_verbose=False

def v(str):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(str)
        sys.stdout.flush()

##########################################################################
##########################################################################
    
def main(options):
    global g_verbose
    g_verbose=options.verbose
    
    for c in options.drives:
        if c not in "01234567": fatal("Invalid drive: %c"%c)

    for c in options.drives:
        name=os.path.join(options.name,c)

        v("%s: "%name)
        
        if os.path.isdir(name): v("exists.")
        else:
            os.makedirs(name)
            v("created.")

        v("\n")

##########################################################################
##########################################################################

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="make new 65Link volume")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")
    
    parser.add_argument("name",
                        metavar="NAME",
                        help="name of volume to create")

    parser.add_argument("drives",
                        metavar="DRIVES",
                        nargs="?",
                        default="02",
                        help="drives to create (default: %(default)s)")

    args=sys.argv[1:]

    options=parser.parse_args(args)
    main(options)
