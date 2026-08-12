#!/usr/bin/python3
import sys,os,os.path,argparse

##########################################################################
##########################################################################

def main2(options):
    track_size_bytes=10*256
    
    def load_ssd(path):
        if path is None:
            data=bytearray(512)
            # 80*10=800=0x320
            data[0x106]=0x03
            data[0x107]=0x02
        else:
            with open(path,'rb') as f: data=f.read()

            if len(data)>80*track_size_bytes:
                sys.stderr.write(f'''WARNING: file larger than 80 tracks will be truncated: {path}\n''')

        return data

    side0=load_ssd(options.side0_path)
    side2=load_ssd(options.side2_path)

    dsd=bytes()

    def get_track(ssd,offset):
        if offset>len(ssd): track=b''
        else: track=ssd[offset:offset+track_size_bytes]
        
        if len(track)<track_size_bytes:
            track+=b'\xe5'*(track_size_bytes-len(track))
            
        return track

    for track in range(0,80):
        offset=track*track_size_bytes

        if offset>len(side0) and offset>len(side2): break

        dsd+=get_track(side0,offset)
        dsd+=get_track(side2,offset)

    if options.output_path is not None:
        with open(options.output_path,'wb') as f: f.write(dsd)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-0',metavar='FILE',dest='side0_path',help='''use .ssd file %(metavar)s for side 0 (blank 80T if not specified)''')
    parser.add_argument('-2',metavar='FILE',dest='side2_path',help='''use .ssd file %(metavar)s for side 2 (blank 80T if not specified)''')
    parser.add_argument('-o',metavar='FILE',dest='output_path',help='''write output .dsd file to %(metavar)s''')
 
    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
