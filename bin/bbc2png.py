#!/usr/bin/python3
import os,os.path,sys,argparse,png,collections
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
    result=[0]*(8//bpp)
    j=0
    for i in range(8):
        result[j]<<=1
        if value&0x80: result[j]|=1
        
        j+=1
        if j==len(result): j=0

        value<<=1
        
    return result

ModeDef=collections.namedtuple("ModeDef",
                               "pc_width_scale pc_height_scale default_palette num_columns row_height")

g_modes={
    0:ModeDef(1,2,[0,7],80,8),    
    1:ModeDef(1,1,[0,1,3,7],80,8),
    2:ModeDef(2,1,range(16),80,8),
    3:ModeDef(1,2,[0,7],80,10),   
    4:ModeDef(1,1,[0,7],40,8),    
    5:ModeDef(2,1,[0,1,3,7],40,8),
    6:ModeDef(1,1,[0,7],40,10),
    8:ModeDef(4,1,range(16),40,8),
}

g_pc_colours=[
    # authentic colours
    (0,0,0),
    (255,0,0),
    (0,255,0),
    (255,255,0),
    (0,0,255),
    (255,0,255),
    (0,255,255),
    (255,255,255),

    # fake colours
    (128,128,128),              # 8 = grey
    (255,128,128),              # 9 = pink
    (0,128,0),                  # 10 = dark green
    (128,128,0),                # 11 = murky yellow
    (0,128,255),                # 12 = sky blue
    (255,128,255),              # 13 = pastel magenta
    (128,255,255),              # 14 = pastel cyan
    (192,192,192),              # 15 = light grey
]

def bbc2png(options):
    global g_verbose
    g_verbose=options.verbose

    if options.mode not in g_modes: fatal("unsupported MODE: %d"%options.mode)
    mode=g_modes[options.mode]

    if len(mode.default_palette)==2: bpp=1
    elif len(mode.default_palette)==4: bpp=2
    elif len(mode.default_palette)==16: bpp=4
    else: assert False,mode.default_palette

    # Decide on screen dimensions.
    num_columns=mode.num_columns if options.num_columns is None else options.num_columns

    # Decide on palette.
    palette=mode.default_palette[:]
    if options.palette is not None:
        if len(options.palette)!=len(palette): fatal("wrong palette size - must be %d"%len(palette))

        palette=[]
        for c in options.palette:
            try: palette.append(int(c,16))
            except ValueError: fatal("bad colour in palette: %c"%c)

    palette=[g_pc_colours[c&(15 if options.pal16 else 7)] for c in palette]

    # Allocate a palette entry for the mode 3/6 gaps.
    blank_index=None
    if mode.row_height>8:
        blank_index=len(palette)
        palette.append((0,0,0))
        
    v("Palette: %s\n"%palette)

    # Read image data.
    with open(options.fname,"rb") as f: data=f.read()
    data=data[options.offset:]
    if options.count is not None: data=data[:options.count]

    # Image must match the 6845 dimensions.
    stride=num_columns*8
    if len(data)%stride!=0: fatal("image data not a multiple of stride %d"%stride)
    num_rows=len(data)//stride

    # Convert.
    width_scale=mode.pc_width_scale if options.pc else 1
    height_scale=mode.pc_height_scale if options.pc else 1
    image=[]
    for row_idx in range(num_rows):
        for scanline_idx in range(mode.row_height):
            row=[]
            if scanline_idx>=8:
                assert blank_index is not None
                row=num_columns*(8//bpp)*[blank_index]
            else:
                offset=row_idx*num_columns*8+scanline_idx
                for x in range(num_columns):
                    byte_indexes=get_palette_indexes(data[offset+x*8],bpp)
                    for index in byte_indexes:
                        for j in range(width_scale): row.append(index)

            for i in range(height_scale): image.append(row)

    if options.output_fname is not None:
        with open(options.output_fname,'wb') as f:
            png.Writer(len(image[0]),len(image),palette=palette).write(f,image)

##########################################################################
##########################################################################
            
def main(args):
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

    parser.add_argument("--pc",
                        action="store_true",
                        help="resize image to a sensible aspect ratio for a PC")

    parser.add_argument("-p",
                        "--palette",
                        default=None,
                        help="specify palette")

    parser.add_argument('--16',
                        dest='pal16',
                        action='store_true',
                        help='use non-BBC colours when converting physical colours 8-15')

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

    modes_list='/'.join([str(x) for x in g_modes.keys()])
    parser.add_argument("mode",
                        type=auto_int,
                        help="MODE screen dump came from - %s"%modes_list)

    options=parser.parse_args(args)
    
    bbc2png(options)
            
##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__": main(sys.argv[1:])
