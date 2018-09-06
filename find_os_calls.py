#!/usr/bin/python
import os,sys,argparse,os.path

##########################################################################
##########################################################################

can_handle_basic=False
try:
    import BBCBasicToText
    can_handle_basic=True
except ImportError: pass

##########################################################################
##########################################################################

def is_basic(contents):
    i=0
    while True:
        if i>=len(contents): return False
        if contents[i]!=0x0D: return False
        if i+1>=len(contents): return False
        if contents[i+1]==0xFF: return True
        if i+3>=len(contents): return False
        if contents[i+3]==0: return False
        
        i+=contents[i+3]

##########################################################################
##########################################################################

def remove(xs,x):
    try:
        xs.remove(x)
    except ValueError:
        pass
        
##########################################################################
##########################################################################
        
def main(options):
    skip_exts=set([os.path.normcase(x) for x in ['.lea',
                                                 '.inf',
                                                 '.mp4',
                                                 '.py']])
    all_file_paths=[]
    for folder_name in options.folder_names:
        for path,folder_names,file_names in os.walk(folder_name):
            remove(folder_names,'.git')
            for file_name in file_names:
                if os.path.normcase(os.path.splitext(file_name))[1] in skip_exts:
                    continue
                
                all_file_paths.append(os.path.join(path,file_name))
                #print all_file_paths[-1]

    print 'found %d files'%len(all_file_paths)

    total_byte_counts=[0]*256
    total_byte_fractions=[0.0]*256
    num_files=0

    num_bytes_total=0
    num_basic=0
    for file_path_idx,file_path in enumerate(all_file_paths):
        try:
            with open(file_path,'rb') as f: data_str=f.read()
                
        except IOError:
            print>>sys.stderr,'WARNING: failed to load: %s'%file_path
            continue
        
        data_arr=[ord(x) for x in data_str]
        
        if is_basic(data_arr):
            num_basic+=1
        else:
            jsr_osgbpb='\x20\xd1\xff'
            jmp_osgbpb='\x4c\xd1\xff'
            jmp_gbpbv='\x6c\x1a\x02'

            if (data_str.find(jsr_osgbpb)>=0 or
                data_str.find(jmp_osgbpb)>=0):# or
                #data_str.find(jmp_gbpbv)>=0):
                print 'OSGBPB: %s'%file_path

        file_byte_counts=[0]*256
        for byte in data_arr: file_byte_counts[byte]+=1
        for i in range(256):
            total_byte_counts[i]+=file_byte_counts[i]
            if len(data_arr)>0:
                total_byte_fractions[i]+=file_byte_counts[i]/float(len(data_arr))
            
        num_files+=1
        num_bytes_total+=len(data_arr)

    print 'examined %d bytes'%num_bytes_total
    print 'found %d BASIC files'%num_basic

    for i in range(256): print '%d,%d,%f'%(i,
                                           total_byte_counts[i],
                                           total_byte_fractions[i]/num_files)

##########################################################################
##########################################################################

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='find BBC Micro code that makes specific OS calls')

    parser.add_argument('folder_names',
                        metavar='FOLDER',
                        nargs='+',
                        help='folder(s) to search in')

    main(parser.parse_args(sys.argv[1:]))
    
