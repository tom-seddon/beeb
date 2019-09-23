#!/usr/bin/python
import sys,os,os.path,glob,argparse,platform,termios,collections,tty

##########################################################################
##########################################################################

def find_device(specified_device):
    if specified_device is not None: return specified_device

    devices=glob.glob('/dev/cu.usbmodem*')
    if len(devices)!=1:
        raise RuntimeError('multiple usbmodem devices found: %s'%(', '.join(devices)))

    return devices[0]
    

##########################################################################
##########################################################################

TCAttr=collections.namedtuple('TCAttr',
                              'iflag oflag cflag lflag ispeed ospeed cc')

class Connection:
    def __init__(self):
        self.verbose=False
        self._fd=-1

    def __enter__(self): return self

    def __exit__(self,exc_type,exc_value,traceback):
        if self._fd>=0:
            os.close(self._fd)
            self._fd=-1

    def _v(self,x):
        if self.verbose:
            sys.stdout.write(x)
            sys.stdout.flush()

    def _init(self):
        if self._fd>=0: return

        device=find_device(self.device)

        self._fd=os.open(device,os.O_RDWR|os.O_APPEND)
        tty.setraw(self._fd)
        attr=TCAttr(*termios.tcgetattr(self._fd))
        attr=attr._replace(ospeed=termios.B230400)
        attr=attr._replace(ispeed=termios.B230400)
        termios.tcsetattr(self._fd,
                          termios.TCSAFLUSH,
                          list(attr))

        self._v('fd=%d; tcgetattr=%s\n'%(self._fd,
                                         TCAttr(*termios.tcgetattr(self._fd))))
        
    def send(self,data,verbose_ok=True):
        self._init()
        if verbose_ok: self._v('Sending: ``%s\'\'\n'%data)
        else: self._v('Sending %d byte(s)\n'%len(data))

        i=0
        while i<len(data):
            self._v('Sending from +%d...\n'%i)
            os.write(self._fd,data[i])
            i+=1
            self._v('Waiting for drain...\n')
            termios.tcdrain(self._fd)

        self._v('All sent.\n')

    def reset(self):
        self._v('Resetting...\n')

        self.wait_for_ready()
        for i in range(3):
            self.send('q')
            self.wait_for_ok()

    def wait_for_ok(self):
        self._v('Waiting for OK...\n')
        if self._wait_for(['OK','\\','|','/','-'])!='OK':
            self._wait_for(['OK'])
        self._wait_for(['\\','|','/','-'])

    def wait_for_ready(self):
        self._v('Waiting for ready...\n')
        self._wait_for(['\\','|','/','-'])

    def _wait_for(self,options):
        self._v('Waiting for one of: %s\n'%(', '.join(options)))
        for i in xrange(10000):
            line=self.readline()
            self._v('Got: ``%s\'\' (%s)\n'%(line,[ord(x) for x in line]))
            if line in options: return line

        raise RuntimeError('MOS switcher wasn\'t ready in time')

    def readline(self):
        self._init()

        line=''
        while True:
            c=os.read(self._fd,1)
            if c=='\r' or c=='\n':
                # just consume leading line breaks.
                if line=='': continue
                else: break
            elif c=='': raise Error('got EOF')
            else: line+=c

        return line

##########################################################################
##########################################################################

# def _recv_thread(fd,cv,buffer):
#     while True:
#         try:
#             c=os.read(fd,1)
#             if c=='': return
#         except IOError: return

#         cv.acquire()
#         buffer.append(ord(c[0]))
#         cv.notifyAll()
#         cv.release()

# def terminal(specified_device):
#     device=find_device(specified_device)

#     fd=os.open(device,os.O_RDWR|os.O_APPEND)

#     cv=threading.Condition()

#     recv_buffer=[]
#     recv_th=threading.Thread(target=_recv_thread,
#                              args=(fd,cv,recv_buffer))

#     while True:
        

#     os.close(fd)
#     fd=-1
