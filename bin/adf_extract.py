#!/usr/bin/python
import os,os.path,sys,collections,argparse,glob,numbers,bbc_inf

# see http://mdfs.net/Docs/Comp/Disk/Format/ADFS

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write('FATAL: %s'%str)
    if str[-1]!='\n': sys.stderr.write('\n')
    sys.exit(1)

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

ADFSFormat=collections.namedtuple('ADFSFormat','num_sides num_tracks num_sectors')
g_adfs_formats={
    'S':ADFSFormat(1,40,16),
    'M':ADFSFormat(1,80,16),
    'L':ADFSFormat(2,80,16),
}

##########################################################################
##########################################################################

def get_24le(data,offset):
    return (data[offset+0]|
            data[offset+1]<<8|
            data[offset+2]<<16)

def get_32le(data,offset):
    return (data[offset+0]|
            data[offset+1]<<8|
            data[offset+2]<<16|
            data[offset+3]<<24)

def bad_format(msg): fatal('bad ADFS format - %s'%msg)

def check_hugo(data,offset,msg):
    if (data[offset+0]!=ord('H') and
        data[offset+1]!=ord('u') and
        data[offset+2]!=ord('g') and
        data[offset+3]!=ord('o')):
        bad_format('Hugo missing: %s'%msg)

def check_checksum(data,what):
    sum=255
    for j in range(254,-1,-1):
        if sum>255: sum=(sum+1)&0xff
        sum+=data[j]
    if (sum&0xff)!=data[255]:
        bad_format('bad checksum for %s - expected $%02x, got $%02x'%(what,sum&0xff,data[255]))

class ADFSImage:
    def __init__(self,data,sequential):
        if len(data)%256!=0:
            bad_format('data size not a multiple of 256 bytes')
            
        check_checksum(data[0:256],'sector 0')
        check_checksum(data[256:512],'sector 1')

        num_sectors=get_24le(data,0xfc)
        pv('%d sector(s) on disk\n'%num_sectors)

        if len(data)!=num_sectors*256:
            bad_format('disk image size mismatch (data is %d sectors (%d bytes), image says %d sectors (%d bytes))'%(len(data)//256,len(data),num_sectors,num_sectors*256))

        self._sectors=[]
        if sequential:
            for i in range(0,len(data),256):
                self._sectors.append(data[i:i+256])
        else:
            if len(data)%(16*256)!=0:
                bad_format('track-interleaved data not a multiple of track size')

            format=None
            for f in g_adfs_formats.values():
                if num_sectors==f.num_sides*f.num_tracks*f.num_sectors:
                    format=f
                    break

            if f is None:
                bad_format('unrecognised disk size - %d sectors (%d bytes)'%(num_sectors,num_sectors*256))

            for i in range(len(data)//256):
                # logical sector order is tracks 0-(N-1) on side 0,
                # then again on side 2.
                sector=i%format.num_sectors
                i/=format.num_sectors
                
                track=i%format.num_tracks
                i/=format.num_tracks

                side=i
                assert side>=0 and side<format.num_sides

                # ADFS images are track-interleaved.
                offset=((track*format.num_sides+side)*format.num_sectors+sector)*256

                self._sectors.append(data[offset:offset+256])

    def get_sector(self,sector):
        assert sector>=0 and sector<len(self._sectors),(sector,len(self._sectors))
        return self._sectors[sector]
            
##########################################################################
##########################################################################

def extract_dir(adf,
                adfs_path,
                dir_sector,
                output_path):
    pv('ADFS dir %s -> PC dir %s...\n'%('.'.join(adfs_path),
                                        output_path))
    
    dir=[]
    for i in range(5): dir+=adf.get_sector(dir_sector+i)

    check_hugo(dir,1,'%s header'%adfs_path)
    check_hugo(dir,0x4fb,'%s footer'%adfs_path)

    for file_idx in range(47):
        offset=5+file_idx*0x1a

        name=''
        for i in range(10):
            c=dir[offset+i]&0x7f
            if c==0 or c==13: break
            name+=chr(c)

        if len(name)==0: continue

        R=(dir[offset+0]&0x80)!=0
        W=(dir[offset+1]&0x80)!=0
        L=(dir[offset+2]&0x80)!=0
        D=(dir[offset+3]&0x80)!=0
        E=(dir[offset+4]&0x80)!=0

        if D:
            child_dir_sector=get_24le(dir,offset+0x16)
            extract_dir(adf,
                        adfs_path+[name],
                        child_dir_sector,
                        os.path.join(output_path,
                                     bbc_inf.get_pc_name(name)))
        else:
            load_addr=get_32le(dir,offset+0xa)
            exec_addr=get_32le(dir,offset+0xe)
            size=get_32le(dir,offset+0x12)
            sector=get_24le(dir,offset+0x16)
            attr=((0x11 if R else 0)|
                  (0x22 if W else 0)|
                  (0x44 if E else 0)|
                  (0x88 if L else 0))

            pc_path=os.path.join(output_path,
                                 bbc_inf.get_pc_name(name))

            pv('ADFS file %s -> PC file %s\n'%('.'.join(adfs_path+[name]),
                                               pc_path))
            
            pv('    (load=%08x exec=%08x size=%u attr=%02x (%s%s%s%s) sector=%06x)\n'%
               (load_addr,
                exec_addr,
                size,
                attr,
                "R" if R else "",
                "W" if W else "",
                "E" if E else "",
                "L" if L else "",
                sector))

            data=[]
            while size>0:
                next_sector=adf.get_sector(sector)
                if len(next_sector)>size:
                    next_sector=next_sector[:size]
                    
                data+=next_sector
                sector+=1
                size-=256

            pc_folder=os.path.dirname(pc_path)
            if not os.path.isdir(pc_folder): os.makedirs(pc_folder)
            
            with open('%s.inf'%pc_path,'wt') as f:
                print>>f,'%s %08x %08x %02x'%(name,load_addr,exec_addr,attr)

            with open(pc_path,'wb') as f:
                f.write(''.join([chr(x) for x in data]))

            
##########################################################################
##########################################################################

def adf_extract(options):
    global g_verbose ; g_verbose=options.verbose

    with open(options.input_path,'rb') as f:
        adf=ADFSImage([ord(x) for x in f.read()],
                      options.sequential)

    extract_dir(adf,
                ['$'],
                2,
                options.output_path)

##########################################################################
##########################################################################
    
def main(args):
    parser=argparse.ArgumentParser(description='extract ADFS disk image to .inf folder')

    parser.add_argument('-v','--verbose',action='store_true',help='be more verbose')
    
    parser.add_argument('-o','--output-dir',dest='output_path',default='.',metavar='DIR',help='write files to %(metavar)s. Default: %(default)s')

    parser.add_argument('--sequential',action='store_true',help='image is in logical sector order rather than track order')

    parser.add_argument('input_path',metavar='FILE',help='read disk image from %(metavar)s')

    adf_extract(parser.parse_args(args))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
