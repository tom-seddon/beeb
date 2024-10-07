#!/usr/bin/python3
import sys,os,os.path,argparse,collections,json,hashlib

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################

LibraryROM=collections.namedtuple('LibraryROM','value')
UnknownROM=collections.namedtuple('UnknownROM','path data')
ROMInfo=collections.namedtuple('ROMInfo','type_ copyright_ title version version_str')

class FileROM:
    def __init__(self,path):
        self._path=path
        self.seen=False

    @property
    def path(self): return self._path

##########################################################################
##########################################################################

def load_rom(f):
    data=f.read(259)
    if len(data)<10: return None # too small

    c=data[7]
    if c+3>len(data): return None # invalid copyright offset
    
    if data[c+0]!=0 or data[c+1]!=ord('(') or data[c+2]!=ord('C') or data[c+3]!=ord(')'):
        return None            # invalid copyright message

    data+=f.read()

    return data

##########################################################################
##########################################################################

def get_bbc_str(data,offset):
    s=''
    i=offset
    while i<len(data) and data[i]!=0:
        if data[i]>=32 and data[i]<126: s+=chr(data[i])
        elif data[i]==9: s+=r'''\t'''
        elif data[i]==13: s+=r'''\r'''
        elif data[i]==10: s+=r'''\n'''
        else: s+=r'''\x%02x'''%data[i]

        i+=1

    return s,i

##########################################################################
##########################################################################

def get_ROM_info(data):
    type_=data[6]
    version=data[8]
    title,title_end=get_bbc_str(data,9)
    copyright_=get_bbc_str(data,data[7]+1)[0]
    if data[7]==title_end: version_str=None
    else: version_str=get_bbc_str(data,title_end+1)[0]

    return ROMInfo(type_,copyright_,title,version,version_str)

##########################################################################
##########################################################################

def get_md5(data): return hashlib.md5(data).hexdigest()

##########################################################################
##########################################################################

def main2(options):
    global g_verbose
    g_verbose=options.verbose
    
    library_ROM_by_md5={}
    
    with open(options.library_json_path,'rb') as f: library_j=json.load(f)
    for platform,roms in library_j['roms'].items():
        for rom in roms:
            for num,rom_data in rom.items():
                name=rom_data['name']
                rom_images=rom_data['rom_images']
                for rom_image in rom_images:
                    for md5,rom_image_data in rom_image.items():
                        assert md5 not in library_ROM_by_md5
                        library_ROM_by_md5[md5]=LibraryROM(value=rom_image_data)

    pv('Library: %d ROMs\n'%len(library_ROM_by_md5))

    unknown_ROM_by_path={}
    num_roms_found=0
    for rom_path in options.rom_paths:
        for folder_path,folder_names,file_names in os.walk(rom_path):
            for file_name in file_names:
                rom_path=os.path.join(folder_path,file_name)
                with open(rom_path,'rb') as f: data=load_rom(f)
                if data is None: continue

                num_roms_found+=1

                hash=get_md5(data)
                if hash in library_ROM_by_md5: continue

                if len(data)==16384 and data[:8192]==data[8192:]:
                    data=data[:8192]
                    hash=get_md5(data)
                    if hash in library_ROM_by_md5: continue

                assert rom_path not in unknown_ROM_by_path
                unknown_ROM_by_path[rom_path]=UnknownROM(path=rom_path,data=data)

    pv('Unknown ROMs on disk: %d/%d\n'%(len(unknown_ROM_by_path),num_roms_found))

    # Remove unknown duplicates.
    old_num_unknown_ROMs_by_path=len(unknown_ROM_by_path)
    paths_by_hash={}
    for rom in unknown_ROM_by_path.values():
        hash=get_md5(rom.data)
        paths_by_hash.setdefault(hash,[]).append(rom.path)

    for hash,paths in paths_by_hash.items():
        if len(paths)>1:
            for i in range(1,len(paths)): del unknown_ROM_by_path[paths[i]]

    pv('Removed duplicates: %d\n'%(old_num_unknown_ROMs_by_path-len(unknown_ROM_by_path)))

    # Remove larger ROMs that were split into chunks.
    old_num_unknown_ROMs_by_path=len(unknown_ROM_by_path)
    def find_sequence(prefix,suffix,count,bases):
        candidates=[]
        i=0
        while i<count:
            found=False
            for base in bases:
                candidate_path='%s%c%s'%(prefix,ord(base)+i,suffix)
                if candidate_path in unknown_ROM_by_path:
                    candidates.append(unknown_ROM_by_path[candidate_path])
                    found=True
                    break
            if not found: break
            i+=1

        if len(candidates)>=2:
            data=b''
            for c in candidates: data+=c.data

            hash=hashlib.md5(data).hexdigest()
            if hash in library_ROM_by_md5:
                return [c.path for c in candidates]

        return None

    for path in list(unknown_ROM_by_path.keys()):
        seq=None
        if path.lower().endswith('a'): seq=find_sequence(path[:-1],'',26,['a','A'])
        elif path.endswith('0'): seq=find_sequence(path[:-1],'',10,['0'])
        else:
            parts=os.path.splitext(path)
            if parts[0].lower().endswith('a'): seq=find_sequence(parts[0][:-1],parts[1],26,['a','A'])
            elif parts[0].endswith('0'): seq=find_sequence(parts[0][:-1],parts[1],10,['0'])

        if seq is not None:
            for path in seq: del unknown_ROM_by_path[path]

    pv('Removed split ROMs; %d\n'%(old_num_unknown_ROMs_by_path-len(unknown_ROM_by_path)))

    for path in sorted(unknown_ROM_by_path.keys()):
        rom=unknown_ROM_by_path[path]
        info=get_ROM_info(rom.data)

        print('%s : %s'%(path,info.title))

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')
    parser.add_argument('library_json_path',metavar='JSON-PATH',help='''read library JSON from %(metavar)s. Default: %(default)s''')
    parser.add_argument('rom_paths',metavar='ROM-PATH',nargs='*',help='''look for BBC Micro ROMs in %(metavar)s''')

    main2(parser.parse_args(argv[1:]))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv)
