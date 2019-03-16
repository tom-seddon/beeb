#!/usr/bin/python
import os,os.path,sys,collections,argparse,glob

# see http://mdfs.net/Docs/Comp/Disk/Format/ADFS

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

def pv(str):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(str)
        sys.stdout.flush()

##########################################################################
##########################################################################

class BeebFile:
    def __init__(self,
                 path,
                 data,
                 dir,
                 name,
                 load_addr,
                 exec_addr,
                 locked):
        self._path=path
        self._data=data
        self._dir=dir
        self._name=name
        self._load_addr=load_addr
        self._exec_addr=exec_addr
        self._locked=locked

    @property
    def path(self): return self._path

    @property
    def data(self): return self._data
    
    @property
    def dir(self): return self._dir
    
    @property
    def name(self): return self._name
    
    @property
    def load_addr(self): return self._load_addr
    
    @property
    def exec_addr(self): return self._exec_addr
    
    @property
    def locked(self): return self._locked

##########################################################################
##########################################################################

# each BeebFile has a dir property, but it's ignored.
class BeebDir:
    def __init__(self,
                 parent,
                 name,
                 items=[]):
        self._parent=parent
        self._name=name
        self._items=[]
        self._name_map={}

    @property
    def name(self): return self._name

    def get_name(self):
        if self._parent is None: return self.name
        else: return self._parent.get_name()+'.'+self.name

    def get_sorted_items(self):
        return sorted(self._items[:],
                      lambda a,b: cmp(a.name.upper(),b.name.upper()))

    def add_file(self,f):
        assert isinstance(f,BeebFile)
        self._add(f)

    def get_or_create_dir(self,name):
        item=self._find(name)
        if item is None:
            d=BeebDir(self,None)
            self._add(d)
            return d
        else:
            if isinstance(item,BeebFile):
                fatal('file already exists: %s.%s'%(self.get_name(),
                                                    item.name))

            return item

    def _find(self,name):
        idx=self._name_map.get(name.upper())
        if idx is None: return None
        return self._items[idx]

    def _add(self,item):
        if len(self._items)==47:
            fatal('too many entries in dir: %s'%self.get_name())

        nameu=item.name.upper()
        if nameu in self._name_map:
            fatal('name already exists: %s.%s'%(self.get_name(),
                                                item.name))

        idx=len(self._items)
        self._name_map[nameu]=idx

        self._items.append(item)

##########################################################################
##########################################################################
    
def create_beeb_file(fname,inf_data):
    if len(inf_data[0])<3:
        print>>sys.stderr,'NOTE: Ignoring %s: BBC name too short: %s'%(fname,inf_data[0])
        return None
        
    if inf_data[0][1]!='.':
        print>>sys.stderr,'NOTE: Ignoring %s: BBC name not a DFS-style name: %s'%(fname,inf_data[0])
        return None
        
    if len(inf_data[0])>12:
        print>>sys.stderr,'NOTE: Ignoring %s: BBC name too long: %s'%(fname,inf_data[0])
        return None

    locked=False
    if len(inf_data)>=4:
        if inf_data[3].lower()=='l': locked=True
        else:
            try:
                attr=int(inf_data[3],16)
                locked=(attr&8)!=0
            except ValueError: pass

    with open(fname,'rb') as f: data=f.read()

    return BeebFile(fname,
                    data,
                    inf_data[0][0],
                    inf_data[0][2:],
                    int(inf_data[1],16),
                    int(inf_data[2],16),
                    locked)

##########################################################################
##########################################################################

def find_beeb_files(options):
    # Use glob.glob to expand the input files. Much more convenient on
    # Windows.
    fnames=[]
    for pattern in options.fnames: fnames+=glob.glob(pattern)

    # Remove anything that doesn't have a .inf file.
    fnames=[x for x in fnames if os.path.isfile(x+'.inf')]

    beeb_files=[]
    for fname in fnames:
        with open(fname+'.inf','rt') as f:
            inf_lines=f.readlines()
            if len(inf_lines)==0:
                # Unclever bodge.
                inf_data=[os.path.basename(fname),'ffffffff','ffffffff']
            else: inf_data=inf_lines[0].split()

        beeb_file=create_beeb_file(fname,inf_data)
        if beeb_file is not None: beeb_files.append(beeb_file)

    return beeb_files

##########################################################################
##########################################################################

ADFSImage=collections.namedtuple('ADFSImage','sectors num_files num_dirs num_bytes num_used_sectors')

# this should really just be a function, but Python's scoping is too
# annoying...
class ADFSImageBuilder:
    def __init__(self,
                 root_dir,
                 disk_id,
                 boot_option,
                 max_num_sectors):
        self._root_dir=root_dir
        self._max_num_sectors=max_num_sectors
        
        self._num_files=0
        self._num_dirs=0
        self._num_bytes=0

        self._sectors=[]

        # book 2 sectors for the free space map - filled in later.
        for i in range(2): self._add_sector(256*[0])

        # build the sectors.
        self._append_dir(root_dir,len(self._sectors))

        self._init_free_space_map(disk_id,
                                  boot_option)

        num_used_sectors=len(self._sectors)

        # expand disk image to the full size.
        while len(self._sectors)<self._max_num_sectors:
            self._add_sector(256*[0])

        self._check()

        # add free space map checksums
        for i in range(2):
            sum=255
            for j in range(254,-1,-1):
                if sum>255: sum=(sum+1)&0xff
                sum+=self._sectors[i][j]
            self._sectors[i][0xff]=sum&0xff

        self._check()

        self._image=ADFSImage(self._sectors,
                              self._num_files,
                              self._num_dirs,
                              self._num_bytes,
                              num_used_sectors)

    @property
    def image(self): return self._image

    def _set_le(self,arr,idx,nbytes,value):
        assert isinstance(value,int)
        for i in range(nbytes):
            arr[idx+i]=value&0xff
            value>>=8

        assert value==0

    def _check(self):
        assert len(self._sectors)<=self._max_num_sectors
        # for i,s in enumerate(self._sectors):
        #     assert isinstance(s,list)
        #     assert len(s)==256
        #     for j in range(256):
        #         assert isinstance(s[j],int)
        #         assert s[j]>=0 and s[j]<=256

    def _init_free_space_map(self,
                             disk_id,
                             boot_option):
        s=self._sectors[0]

        if len(self._sectors)<self._max_num_sectors:
            # There's just one big block of free space at the end...
            self._set_le(self._sectors[0],0,3,
                         len(self._sectors))
        
            self._set_le(self._sectors[1],0,3,
                         self._max_num_sectors-len(self._sectors))

            self._sectors[1][0xfe]=3

        # Set disk size.
        self._set_le(self._sectors[0],0xfc,3,self._max_num_sectors)

        # Set disk identifier.
        self._set_le(self._sectors[1],0xfb,2,disk_id)

        # Set boot option.
        self._sectors[1][0xfd]=boot_option

        self._check()

    def _add_sector(self,data):
        if len(self._sectors)==self._max_num_sectors:
            fatal('disk image is too large')

        self._sectors.append(data)

    def _append_file(self,f):
        self._num_files+=1
        self._num_bytes+=len(f.data)
        
        file_sector_idx=len(self._sectors)
        
        data=[ord(x) for x in f.data]
        while len(data)%256!=0: data.append(0)
        for i in range(0,len(data),256): self._add_sector(data[i:i+256])
        
        return file_sector_idx

    def _append_dir(self,dir,parent_dir_sector_idx):
        self._num_dirs+=1
        
        items=dir.get_sorted_items()

        # book 5 sectors for this directory.
        dir_sector_idx=len(self._sectors)
        for i in range(5): self._add_sector(None)

        # initially create as flat array of 5 sectors.
        data=5*256*[0]

        data[1]=ord('H')
        data[2]=ord('u')
        data[3]=ord('g')
        data[4]=ord('o')

        idx=5
        for item in items:
            for i in range(len(item.name)): data[idx+i]=ord(item.name[i])

            data[idx+0]|=0x80   # readable

            if isinstance(item,BeebFile):
                if not item.locked: data[idx+1]|=0x80 # writeable
                self._set_le(data,idx+0x0a,4,item.load_addr)
                self._set_le(data,idx+0x0e,4,item.exec_addr)
                self._set_le(data,idx+0x12,4,len(item.data))
                self._set_le(data,idx+0x16,3,self._append_file(item))
            elif isinstance(item,BeebDir):
                data[idx+3]|=0x80 # is directory
                
                # presumably load, exec and length are irrelevant?

                self._set_le(data,idx+0x16,3,
                             self._append_dir(item,dir_sector_idx))

            else: assert(False)

            # presumably sequence number can be zero?

            idx+=0x1a

        assert idx<=0x4cb

        # fill in small directory footer.
        for i in range(len(dir.name)): data[0x4cc+i]=ord(dir.name[i])
        self._set_le(data,0x4d6,3,parent_dir_sector_idx)

        # copy header to footer.
        for i in range(5): data[0x4fa+i]=data[0x000+i]

        # split directory into sectors
        for i in range(5):
            assert self._sectors[dir_sector_idx+i] is None
            self._sectors[dir_sector_idx+i]=data[i*256:i*256+256]

        return dir_sector_idx
    
##########################################################################
##########################################################################

ADFSFormat=collections.namedtuple('ADFSFormat','num_sides num_tracks num_sectors')
g_adfs_formats={
    'S':ADFSFormat(1,40,16),
    'M':ADFSFormat(1,80,16),
    'L':ADFSFormat(2,80,16),
}

def get_formats_text():
    formats=[]

    for k,v in g_adfs_formats.iteritems():
        formats.append('%s (%dx%dx%d)'%(k,
                                        v.num_sides,
                                        v.num_tracks,
                                        v.num_sectors))

    return ', '.join(formats)

def main(options):
    global g_verbose ; g_verbose=options.verbose

    format=g_adfs_formats.get(options.type.upper())
    if format is None: fatal('unknown ADFS format: %s'%options.type)

    if options.disk_id is None:
        options.disk_id=ord(os.urandom(1))|ord(os.urandom(1))<<8
    else:
        if options.disk_id<0 or options.disk_id>65536:
            fatal('invalid disk identifier: 0x%04x'%(options.disk_id))

    beeb_files=find_beeb_files(options)

    root_dir=BeebDir(None,'$')

    # Form ADFS tree structure.
    for f in beeb_files:
        if f.dir=='$': root_dir.add_file(f)
        else:
            d=root_dir.get_or_create_dir(f.dir)
            d.add_file(f)

    # Build ADFS image.
    image=ADFSImageBuilder(root_dir,
                           options.disk_id,
                           options.opt4,
                           format.num_sides*format.num_tracks*format.num_sectors).image

    pv('%d bytes in %d files/%d dirs\n'%(image.num_bytes,
                                         image.num_files,
                                         image.num_dirs))
    pv('%d sectors (%d bytes) used\n'%(image.num_used_sectors,
                                       image.num_used_sectors*256))

    if options.output_path is not None:
        # Create output file data.
        data=[]
        for track in range(format.num_tracks):
            for side in range(format.num_sides):
                for sector in range(format.num_sectors):
                    data+=image.sectors[side*(format.num_tracks*
                                              format.num_sectors)+
                                        track*format.num_sectors+
                                        sector]
        data=''.join([chr(x) for x in data])
        with open(options.output_path,'wb') as f: f.write(data)

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="make ADFS disk image from .inf folder")

    parser.add_argument("-v","--verbose",action="store_true",help="be more verbose")
    
    parser.add_argument('-o','--output',dest='output_path',default=None,metavar='FILE',help='write ADFS disk image to %(metavar)s')

    parser.add_argument('--disk-id',metavar='ID',type=auto_int,default=None,help='set disk identifier to %(metavar)s (default is random)')

    parser.add_argument('-4','--opt4',metavar='VALUE',default=0,type=int,help='set *OPT4 option to %(metavar)s')

    parser.add_argument('-t','--type',metavar='TYPE',default='L',help='specify ADFS format - %(metavar)s can be one of: '+get_formats_text()+'. Default: %(default)s')
    
    parser.add_argument("fnames",nargs="*",metavar="FILE",default=[],help="file(s) to put in disk image (non-BBC files will be ignored)")

    args=sys.argv[1:]
    options=parser.parse_args(args)
    main(options)
    
