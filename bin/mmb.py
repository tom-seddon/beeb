#!/usr/bin/python3
import sys,os,os.path,argparse,collections,glob

##########################################################################
##########################################################################

# https://github.com/hoglet67/MMFS/wiki/MMB-File-Format

# Type: 00=RO, 0F=RW, F0=Unformatted, FF=Invalid

TYPE_RO=0x00
TYPE_RW=0x0f
TYPE_UNFORMATTED=0xf0
TYPE_INVALID=0xff

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################
        
def fatal(x):
    sys.stderr.write('FATAL: %s\n'%x)
    sys.exit(1)

##########################################################################
##########################################################################

def is_valid_disk_type(type):
    return type in [TYPE_RO,TYPE_RW,TYPE_UNFORMATTED,TYPE_INVALID]

def get_disk_type_str(type):
    if type==TYPE_RO: return 'ro'
    elif type==TYPE_RW: return 'rw'
    elif type==TYPE_UNFORMATTED: return 'un'
    elif type==TYPE_INVALID: return 'xx'
    else: return '%02X'%type

##########################################################################
##########################################################################

def is_valid_disk_name_char(c): return ord(c)>=32 and ord(c)<127

##########################################################################
##########################################################################

SSD_SIZE=80*10*256
MMB_SIZE=512*16+511*SSD_SIZE
MMB_HEADER=b'\x00\x01\x02\x03'+12*b'\x00'

class MMB:
    def __init__(self,data,path):
        self._path=path
        self._data=data

        if len(data)!=MMB_SIZE:
            self._error('wrong size be an MMB file')
        
        if data[0:16]!=MMB_HEADER:
            self._error('not an MMB file')

        for i in range(511):
            type=self.get_disk_type(i)
            if not is_valid_disk_type(type):
                self._error('invalid disk type (0x%02X) for disk %d'%(type,i))

    def make_mutable(self): self._data=bytearray(self._data)

    @property
    def data(self): return self._data
            
    def _error(self,message):
        if self._path is not None: prefix='%s: '%self._path
        else: prefix=''

        fatal(prefix+message)
                
    def _get_metadata_offset(self,index):
        assert index>=0 and index<511,index
        return 16+index*16

    def _get_contents_offset(self,index):
        assert index>=0 and index<511,index
        return 512*16+index*SSD_SIZE

    def get_disk_type(self,index):
        i=self._get_metadata_offset(index)
        return self._data[i+15]

    def set_disk_type(self,index,type):
        i=self._get_metadata_offset(index)
        assert is_valid_disk_type(type),hex(type)
        self._data[i+15]=type

    def get_disk_name(self,index):
        i=self._get_metadata_offset(index)

        n=0
        while n<12 and self._data[i+n]!=0: n+=1

        return self._data[i:i+n].decode('ascii')

    def set_disk_name(self,index,name):
        assert len(name)<12
        i=self._get_metadata_offset(index)

        for j in range(12):
            if j<len(name):
                assert is_valid_disk_name_char(name[j])
                self._data[i+j]=ord(name[j])
            else: self._data[i+j]=0

    def set_disk_contents(self,index,contents):
        assert len(contents)<=SSD_SIZE
        i=self._get_contents_offset(index)
        for j in range(len(contents)): self._data[i+j]=contents[j]
        for j in range(len(contents),SSD_SIZE): self._data[i+j]=0

    def save(self):
        assert self._path is not None
        with open(self._path,'wb') as f: f.write(self._data)

##########################################################################
##########################################################################

def load_data(path):
    try:
        with open(path,'rb') as f: return f.read()
    except FileNotFoundError: fatal('file not found: %s'%path)

def load_mmb_from_file(path): return MMB(load_data(path),path)

##########################################################################
##########################################################################

def ls_cmd(options):
    mmb=load_mmb_from_file(options.input_path)

    for i in range(511):
        type=mmb.get_disk_type(i)
        if options.all or type==0x00 or type==0x0f:
            line='%03d. '%i
            name=mmb.get_disk_name(i)
            if options.long:
                line+='%-14s %s'%(name,
                                  get_disk_type_str(mmb.get_disk_type(i)))
            else: line+=name
            print(line)
            
##########################################################################
##########################################################################

def create_cmd(options):
    if not options.force:
        if os.path.isfile(options.output_path):
            fatal('%s: file exists'%options.output_path)

    mmb=MMB(MMB_HEADER+(MMB_SIZE-len(MMB_HEADER))*b'\x00',
            options.output_path)
    mmb.make_mutable()

    for i in range(511): mmb.set_disk_type(i,0xf0)

    mmb.save()

##########################################################################
##########################################################################

def set_cmd(options):
    mmb=load_mmb_from_file(options.mmb_path)
    mmb.make_mutable()

    if options.name is not None:
        if len(options.input_paths)>1:
            fatal('''can't set name if multiple disks specified''')
            
        if len(options.name)>12: fatal('name too long')
        mmb.set_disk_name(options.index,options.name)

    # expand globs
    ssd_paths=[]
    for ssd_path in options.ssd_paths:
        paths=glob.glob(ssd_path)
        for path in paths:
            if path not in ssd_paths: ssd_paths.append(path)

    if len(ssd_paths)==0: fatal('paths did not match any files')
    
    index=options.index
    for ssd_path in ssd_paths:
        ssd=load_data(ssd_path)
        if len(ssd)>SSD_SIZE: fatal('%s: too large to be a .ssd'%len(ssd))
        mmb.set_disk_contents(index,ssd)

        mmb.set_disk_type(index,
                          TYPE_RO if options.read_only else TYPE_RW)

        if options.name is None:
            name=os.path.splitext(os.path.basename(ssd_path))[0]
            mmb.set_disk_name(index,name)

        index+=1
        
    mmb.save()

##########################################################################
##########################################################################

def auto_int(x): return int(x,0)

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-v','--verbose',dest='g_verbose',action='store_true',help='''be more verbose''')
    parser.set_defaults(fun=None)
    subparsers=parser.add_subparsers()

    def add_subparser(fun,name,**kwargs):
        subparser=subparsers.add_parser(name,**kwargs)
        subparser.set_defaults(fun=fun)
        return subparser

    ls_parser=add_subparser(ls_cmd,'ls',help='''list contents of mmb''')
    ls_parser.add_argument('input_path',metavar='FILE',help='''read %(metavar)s''')
    ls_parser.add_argument('-a','--all',action='store_true',help='''always print all entries''')
    ls_parser.add_argument('-l','--long',action='store_true',help='''show more details''')

    create_parser=add_subparser(create_cmd,'create',help='''create new blank mmb''')
    create_parser.add_argument('output_path',metavar='FILE',help='''write to %(metavar)s''')
    create_parser.add_argument('-f','--force',action='store_true',help='''proceed even if file exists''')

    set_parser=add_subparser(set_cmd,'set',help='''set disk in MMB''')
    set_parser.add_argument('mmb_path',metavar='MMB',help='''modify MMB file %(metavar)s''')
    set_parser.add_argument('-n',dest='name',metavar='NAME',help='''set name to %(metavar)s (will be set based on disk file name if not provided) (only valid if 1 disk image specified)''')
    set_parser.add_argument('-r','--read-only',action='store_true',help='''mark disk(s) as read-only''')
    set_parser.add_argument('index',type=auto_int,metavar='INDEX',help='''set disk(s) starting from index %(metavar)s''')
    set_parser.add_argument('ssd_paths',metavar='SSD',nargs='+',help='''set disk contents from %(metavar)s (wildcards will be expanded)''')

    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    global g_verbose
    g_verbose=options.g_verbose

    options.fun(options)

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
