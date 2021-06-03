
from __future__ import print_function
import os, sys, struct, time
import os.path
from os.path import join
from serial import Serial
from binascii import hexlify
############################################################################
PYTHON2 = sys.version_info[0] < 3  # True if on pre-Python 3
############################################################################

DEBUG = False
def DBG(s=''):
    if DEBUG:
        print(s)

def ERROR(message):
    print("\nERROR: {}".format(message) )
    time.sleep(0.1)
    exit(1)

def ASSERT(flag, message):
    if flag == False:
        ERROR(message)

def PB_BEGIN(text):
    if DEBUG == False:
        print(text, end='')

def PB_STEP():
    if DEBUG == False:
        print('=', end='')

def PB_END():
    if DEBUG == False:
        print("> DONE")

def PrintHex(s):
    if False == PYTHON2:
        if str == type(s):
            s = bytearray(s, 'utf-8')
    return hexlify(s).decode("ascii").upper()

CMD_EfsHello        =  0  # Parameter negotiation packet
CMD_EfsQuery        =  1  # Send information about EFS2 params
CMD_EfsOpen         =  2  # Open a file
CMD_EfsClose        =  3  # Close a file
CMD_EfsRead         =  4  # Read a file
CMD_EfsWrite        =  5  # Write a file
CMD_EfsSymlink      =  6  # Create a symbolic link
CMD_EfsReadLink     =  7  # Read a symbolic link
CMD_EfsUnlink       =  8  # Remove a symbolic link or file
CMD_EfsMkdir        =  9  # Create a directory
CMD_EfsRmdir        = 10  # Remove a directory
CMD_EfsOpenDir      = 11  # Open a directory for reading
CMD_EfsReadDir      = 12  # Read a directory
CMD_EfsCloseDir     = 13  # Close an open directory

EFS_HEADER          = 0x017E
EFS_FOOTER          = 0x7E
CMD_SUB_ID          = 0x3E4B

class QDL:
    def __init__(self, ser):
        self.s = ser

    def read(self, command):
        b = b''
        rx = self.s.read(8) # # 7E01 1400 4B3E 0500 ... pyload
        b += rx
        ASSERT(8 == len(rx), 'read() header size')
        a = struct.unpack("<HHHH", rx)
        ASSERT(EFS_HEADER == a[0], 'read() header' + PrintHex(b))
        ASSERT(CMD_SUB_ID == a[2], 'read() command sub id' + PrintHex(b))
        ASSERT(command    == a[3], 'read() command' + PrintHex(b))
        SIZE = a[1]
        data = self.s.read(SIZE - 4) # read pyload
        b += data
        ASSERT(SIZE - 4 == len(data), 'read data size')
        rx = self.s.read(1) # read footer 7E
        b += rx
        ASSERT(1 == len(rx), 'read() footer size')
        ASSERT(b'\x7E' == rx, 'read() footer')
        DBG('[{:02X}] <<<'.format(command) + PrintHex(b))
        PB_STEP()
        return data

    def write(self, command, buffer):
        DBG()
        tx = struct.pack("<HHHH",EFS_HEADER, len(buffer) + 4, CMD_SUB_ID, command) + buffer + b'\x7E'
        if len(tx) > 64:
            DBG('[{:02X}] >>>'.format(command) + PrintHex(tx[:64]) + ' ...')
        else:
            DBG('[{:02X}] >>>'.format(command) + PrintHex(tx))
        PB_STEP()
        return self.s.write(tx)

    def OpenFile(self, fileName, flag = 0, mode = 0):
        self.write(CMD_EfsOpen, struct.pack("<II", flag, mode) + fileName )
        res = self.read(CMD_EfsOpen)
        a = struct.unpack("<II", res) # FD, ERR
        DBG('[OpenFile] ' + PrintHex(res))
        ASSERT(a[0] != 0xFFFFFFFF, 'OpenFile() ' + PrintHex(res) )
        pass

    def WriteFile(self, fileName):
        fd = open(fileName, 'rb')
        page = 0
        data = 1
        while data:
            data = fd.read(1024)
            if b'' == data:
                DBG('[WriteFile] EOF')
                break
            self.write(CMD_EfsWrite, struct.pack("<II", 0, page) + data )
            res = self.read(CMD_EfsWrite)
            DBG('[WriteFile] ' + PrintHex(res)) # 7E01 1400 4B3E 0500 [00000000 00000000 FFFFFFFF 09000000] 7E
            a = struct.unpack("<IIII", res) # FD OFFSET WRITED ERROR
            ASSERT(a[2] != 0xFFFFFFFF, 'WriteFile() ' + PrintHex(res) )
            page += 1024
        fd.close()

    def CloseFile(self):
        self.write(CMD_EfsClose, b'\x00\x00\x00\x00')
        self.read(CMD_EfsClose)

    def OpenDir(self, dir):
        self.write(CMD_EfsOpenDir, dir)
        self.read(CMD_EfsOpenDir)

    def CloseDir(self):
        self.write(CMD_EfsCloseDir, b'\x01\x00\x00\x00')
        self.read(CMD_EfsCloseDir)

    def wr(self, tx, rx, test = False):
        DBG('W> ' +PrintHex(tx))
        self.s.write(tx)
        rs = self.s.read(len(rx))
        DBG('R< ' + PrintHex(rs))
        ASSERT(b'' != rs, 'connect no response')
        if test:
            ASSERT(len(rs) == len(rx), 'rd len')
            ASSERT(rs == rx, 'rd data')
        DBG()

    def connect(self):
        self.s.timeout = 1
        self.wr(b'\x0C\x14\x3A\x7E',                b'\x13\x0C\xD2\x7A\x7E'                ) # unknown commands and answers
        self.wr(b'\x4B\x04\x0E\x00\x0D\xD3\x7E',    b'\x13\x4B\x04\x0E\x00\x28\x49\x7E'    ) # init, get info ???
        self.wr(b'\x4B\x08\x02\x00\x0E\xDF\x7E',    b'\x4B\x08\x02\x00\x01\x50\x08\x7E'    )
        self.wr(b'\x4B\x12\x18\x02\x01\x00\xD2\x7E',b'\x4B\x12\x18\x02\x01\x00\xAA\xF0\x7E')
        DBG('CONNECT')

def bg96_upload(com_port, dir):
    ser = Serial(com_port, 115200 )
    q = QDL(ser)
    PB_BEGIN( 'CONNECTING TO DM-PORT <' )
    q.connect()
    PB_END()

    PB_BEGIN( 'WRITE OEM_APP_PATH <' )
    q.OpenFile(b'/datatx/oem_app_path.ini\0', 0x241, 0x1B6)
    q.WriteFile( join(dir, 'oem_app_path.ini') )
    q.CloseFile()
    PB_END()

    PB_BEGIN( 'WRITE PROGRAM <' )
    q.OpenFile(b'/datatx/program.bin\0', 0x241, 0x1B6)
    q.WriteFile( join(dir, 'program.bin') )
    q.CloseFile()

    ser.close()
    PB_END()
