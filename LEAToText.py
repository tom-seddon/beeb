#!env python
import sys,struct,os,os.path,sys

translate={
    "_sp":chr(32+0),"_xm":chr(32+1),"_dq":chr(32+2),"_ha":chr(32+3),"_do":chr(32+4),"_pc":chr(32+5),"_am":chr(32+6),"_sq":chr(32+7),
    "_rb":chr(32+8),"_lb":chr(32+9),"_as":chr(32+10),"_pl":chr(32+11),"_cm":chr(32+12),"_mi":chr(32+13),"_pd":chr(32+14),"_fs":chr(32+15),
    "0":chr(32+16),"1":chr(32+17),"2":chr(32+18),"3":chr(32+19),"4":chr(32+20),"5":chr(32+21),"6":chr(32+22),"7":chr(32+23),"8":
    chr(32+24),"9":chr(32+25),"_co":chr(32+26),"_sc":chr(32+27),"_st":chr(32+28),"_eq":chr(32+29),"_lt":chr(32+30),"_qm":chr(32+31),
    "_at":chr(32+32),"A":chr(32+33),"B":chr(32+34),"C":chr(32+35),"D":chr(32+36),"E":chr(32+37),"F":chr(32+38),"G":chr(32+39),
    "H":chr(32+40),"I":chr(32+41),"J":chr(32+42),"K":chr(32+43),"L":chr(32+44),"M":chr(32+45),"N":chr(32+46),"O":chr(32+47),
    "P":chr(32+48),"Q":chr(32+49),"R":chr(32+50),"S":chr(32+51),"T":chr(32+52),"U":chr(32+53),"V":chr(32+54),"W":chr(32+55),
    "X":chr(32+56),"Y":chr(32+57),"Z":chr(32+58),"_hb":chr(32+59),"_bs":chr(32+60),"_bh":chr(32+61),"_po":chr(32+62),"_un":chr(32+63),
    "_bq":chr(32+64),"a":chr(32+65),"b":chr(32+66),"c":chr(32+67),"d":chr(32+68),"e":chr(32+69),"f":chr(32+70),"g":chr(32+71),
    "h":chr(32+72),"i":chr(32+73),"j":chr(32+74),"k":chr(32+75),"l":chr(32+76),"m":chr(32+77),"n":chr(32+78),"o":chr(32+79),
    "p":chr(32+80),"q":chr(32+81),"r":chr(32+82),"s":chr(32+83),"t":chr(32+84),"u":chr(32+85),"v":chr(32+86),"w":chr(32+87),
    "x":chr(32+88),"y":chr(32+89),"z":chr(32+90),"_cb":chr(32+91),"_ba":chr(32+92),"_bc":chr(32+93),"_no":chr(32+94),
}

def get_bbc_file_name(pc_file_name):
    src=os.path.splitext(os.path.split(pc_file_name)[1])[0]
    dest=""

    i=0
    while i<len(src):
        if src[i]=='_':
            key=src[i:i+3]
            if key not in translate:
                print>>sys.stderr,"FATAL: unknown char \"%s\""%key
                sys.exit(1)
            dest+=translate[key]
            i+=3
        else:
            dest+=src[i]
            i+=1

    return dest[0]+"."+dest[1:]
    
if __name__=="__main__":
    for fname in sys.argv[1:]:
        with open(fname,"rb") as f:
            data=f.read()
            if len(data)==12:
                l,e,a=struct.unpack("<III",data)
                print "%-10s %08X %08X %s"%(get_bbc_file_name(fname),
                                            l,
                                            e,
                                            "L" if (a&8) else "")
