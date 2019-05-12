##########################################################################
##########################################################################

# \ / : * ? " < > |
quote_chars='/<>:"\\|?* .#'

def get_pc_name(bbc_name):
    '''get PC file name part for BBC file name part.

Chars invalid on PC will be escaped. Alpha chars will be upper-cased.

When using this for a DFS-style name, use it separately for the directory char and the name string.)'''
    pc_name=''
    for c in bbc_name:
        if ord(c)<32 or ord(c)>126 or c in quote_chars:
            pc_name+='#%02x'%ord(c)
        else: pc_name+=c.upper()
    return pc_name

##########################################################################
##########################################################################
