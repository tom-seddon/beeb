#!env python
import os,os.path,sys,argparse,PIL.Image,collections
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

def get_palette_indexes(value,bpp):
    result=[0]*(8/bpp)
    j=0
    for i in range(8):
        result[j]<<=1
        if value&0x80: result[j]|=1
        
        j+=1
        if j==len(result): j=0

        value<<=1
        
    return result

def get_rgb(phys): return (255 if phys&1 else 0,255 if phys&2 else 0,255 if phys&4 else 0)

ModeDef=collections.namedtuple("ModeDef","bpp palette")

def main(options):
    global g_verbose
    g_verbose=options.verbose

    if options.mode<0 or options.mode>6: fatal("unsupported MODE: %d"%options.mode)

    palettes={
        1:[0,7],
        2:[0,1,3,7],
        4:range(8)*2,
    }

    # Get mode properties.
    bpp=[ 1,2,4,1,1,2,1][options.mode]
    fast=options.mode<4

    # Decide on 6845 column count.
    if options.num_columns is None:
        if fast: num_columns=80
        else: num_columns=40
    else: num_columns=options.num_columns

    # Decide on palette.
    palette=palettes[bpp]
    if options.palette is not None:
        if len(options.palette)!=len(palette): fatal("wrong palette size - must be %d"%len(palette))

        for c in options.palette:
            if c not in "01234567": fatal("bad colour in palette: %c"%c)

        palette=[int(c) for c in options.palette]
        
    v("Palette: %s\n"%palette)

    # Read image data.
    with open(options.fname,"rb") as f: data=[ord(x) for x in f.read()]

    data=data[options.offset:]
    if options.count is not None: data=data[:options.count]

    # Image must have an exact number of 6845 character rows.
    stride=num_columns*8
    if len(data)%stride!=0: fatal("image data not a multiple of stride %d"%stride)
    num_rows=len(data)/stride

    # Convert.
    image=PIL.Image.new("RGB",(num_columns*8/bpp,num_rows*8))
    for row in range(num_rows):
        for y in range(8):
            offset=row*num_columns*8+y
            indexes=[]
            for x in range(num_columns): indexes+=get_palette_indexes(data[offset+x*8],bpp)
            #v("%s\n"%indexes)
            for x in range(len(indexes)): image.putpixel((x,row*8+y),get_rgb(palette[indexes[x]]))

    if options.resize: image=image.resize((640,512),PIL.Image.NEAREST)

    if options.output_fname is not None: image.save(options.output_fname)

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="convert BBC Micro screen dump")
    
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")

    parser.add_argument("-c",
                        dest="num_columns",
                        type=auto_int,
                        default=None,
                        help="specify number of 6845 columns (if not using the default for mode)")

    parser.add_argument("-o",
                        dest="output_fname",
                        metavar="FILE",
                        default=None,
                        help="file to save image to")

    parser.add_argument("-r",
                        "--resize",
                        action="store_true",
                        help="resize image to 640x512")

    parser.add_argument("-p",
                        "--palette",
                        default=None,
                        help="specify palette")

    parser.add_argument("-d",
                        "--offset",
                        metavar="OFFSET",
                        type=auto_int,
                        default=0,
                        help="offset of image data in file (default: %(default)s)")

    parser.add_argument("-n",
                        "--count",
                        metavar="COUNT",
                        type=auto_int,
                        default=None,
                        help="number of bytes of image data in file (default: all data starting from offset)")

    parser.add_argument("fname",
                        metavar="FILE",
                        help="file to read screen dump from")

    parser.add_argument("mode",
                        type=auto_int,
                        help="MODE screen dump came from")

    args=sys.argv[1:]

    options=parser.parse_args(args)
    
    main(options)
