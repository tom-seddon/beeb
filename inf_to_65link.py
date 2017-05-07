#!/usr/bin/python
import os,os.path,sys,argparse,glob,struct

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

convert_to_65link_char={
    " ":"_sp", "!":"_xm", "\"":"_dq", "#":"_ha",
    "$":"_do", "%":"_pc", "&":"_am", "'":"_sq", "(":"_rb", ")":"_lb",
    "*":"_as", "+":"_pl", ",":"_cm", "-":"_mi", ".":"_pd", "/":"_fs",
    ":":"_co", ";":"_sc", "<":"_st", "=":"_eq", ">":"_lt", "?":"_qm",
    "@":"_at", "[":"_hb", "\\":"_bs", "]":"_bh", "^":"_po", "_":"_un",
    "`":"_bq", "{":"_cb", "|":"_ba", "}":"_bc", "~":"_no",
}

def get_65link_name(bbc_name):
    result=""
    for i,c in enumerate(bbc_name):
        if i==1 and c==".": continue
        result+=convert_to_65link_char.get(c,c)
    return result

##########################################################################
##########################################################################

def main(options):
    global g_verbose
    g_verbose=options.verbose

    inf_fnames=[]
    for f in glob.glob(os.path.join(options.input_folder,"*")):
        base,ext=os.path.splitext(f)
        if ext.lower()==".inf":
            if os.path.isfile(base):
                inf_fnames.append(f)

    if options.output_folder is not None:
        if not os.path.isdir(options.output_folder):
            os.makedirs(options.output_folder)

    bbc_names=set()
    for inf_fname in inf_fnames:
        with open(inf_fname,"rt") as f: parts=f.readline().strip().split()

        bbc_name=parts[0]
        if bbc_name in bbc_names: fatal("duplicated name: %s"%bbc_name)
        bbc_names.add(bbc_name)
        
        bbc_load=int(parts[1],16) if len(parts)>1 else None
        bbc_exec=int(parts[2],16) if len(parts)>2 else None
        bbc_length=int(parts[3],16) if len(parts)>3 else None
        bbc_locked=len(parts)>4 and parts[4] in ["L","Locked"]

        if bbc_exec&0xffff0000: bbc_exec|=0xffff0000
        if bbc_load&0xffff0000: bbc_load|=0xffff0000

        with open(os.path.splitext(inf_fname)[0],"rb") as f: data=f.read()

        if len(data)!=bbc_length: fatal("length mismatch: %s"%bbc_name)

        output_fname=get_65link_name(bbc_name)
        if options.output_folder is not None:
            output_fname=os.path.join(options.output_folder,
                                      output_fname)
        
        v("%-15s %s %08X %08X %08X -> %s\n"%(bbc_name,
                                             "L" if bbc_locked else " ",
                                             bbc_load,
                                             bbc_exec,
                                             bbc_length,
                                             output_fname))

        with open(output_fname,"wb") as f: f.write(data)
        with open(output_fname+".lea","wb") as f:
            f.write(struct.pack("<III",
                                bbc_load,
                                bbc_exec,
                                8 if bbc_locked else 0))

##########################################################################
##########################################################################
        
if __name__=="__main__":
    parser=argparse.ArgumentParser(description="convert .INF files to 65Link volume")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")

    parser.add_argument("-o",
                        dest="output_folder",
                        metavar="FOLDER",
                        default=None,
                        help="put 65Link files in %(metavar)s (will be created if it doesn't exist)")

    parser.add_argument(dest="input_folder",
                        metavar="FOLDER",
                        help="read INF files from %(metavar)s")

    main(parser.parse_args(sys.argv[1:]))
    
