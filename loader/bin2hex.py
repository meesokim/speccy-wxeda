#!/usr/bin/env python3
"""
File: bin2hex.py
Converts a binary file into intel hex format. For usage try $bin2hex.py -h
License
The MIT License
Permission is hereby granted, free of charge, to any person obtaining a
copy of this hardware, software, and associated documentation files (the
"Product"), to deal in the Product without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Product, and to permit
persons to whom the Product is furnished to do so, subject to the
following conditions:
The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Product.
THE PRODUCT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
PRODUCT OR THE USE OR OTHER DEALINGS IN THE PRODUCT.
"""

import sys
import os
import errno
import optparse
import struct

HEX_TYPE_DATA = 0
HEX_TYPE_EOF = 1
HEX_TYPE_EXT_SEG_ADDRESS = 2
HEX_TYPE_START_SEG_ADDRESS = 3
HEX_TYPE_EXT_LINEAR_ADDRESS = 4
HEX_TYPE_START_LINEAR_ADDRESS = 5

HEX_ALLOWED_ADDRESS_TYPES ={
                            0:(1<<16)-1,
                            2:(1<<20)-1,
                            4:(1<<32)-1,
                            }

class HexRecord:
    def __init__(self, type, data, checksum = None, address = 0):
        self.__type = type
        self.__data = data
        self.__length = len([x for x in data])
        self.__address = address

        self.__checksum = self.__length + (address >> 8) + (address & 0xFF) + type
        for b in data:
            self.__checksum += b
        self.__checksum = (~self.__checksum) + 1
        self.__checksum = self.__checksum & 0xFF
        if (checksum is not None) and (self.__checksum != checksum):
            raise Exception("Error: Checksum does not match. Calculated %02X. Given %02X." % (self.__checksum, checksum))

    def getType(self):
        return self.__type

    def getData(self):
        return self.__data

    def getAddress(self):
        return self.__address

    def getRecord(self):
        # return string representation of the record.
        recordstr = ":%02X%04X%02X%s%02X" % (self.__length,
                                             self.__address,
                                             self.__type,
                                             "".join(["%02X" % b for b in self.__data]),
                                             self.__checksum)
        return recordstr

    def write(self, stream=sys.stdout):
        # write the record to stream
        stream.write(":%02X%04X%02X" % (self.__length, self.__address, self.__type))
        for b in self.__data:
            stream.write("%02X" % b)
        stream.write("%02X\n" % self.__checksum)


def readHexFile(stream):
    records = []
    lineNum = 0
    for line in stream:
        lineNum += 1
        line = line.strip()
        if len(line) == 0:
            break

        if line[0] != ":":
            raise Exception("Error on line %d. Record does not start with ':' character. Starts with '%s'." % (lineNum, line[0]))

        byteCount = int(line[1:3], 16)
        address = int(line[3:7], 16)
        type = int(line[7:9], 16)
        if len(line) != (11 + 2*byteCount):
            raise Exception("Bad byteCount on line %d lineNum. Line length is %d chars, expected %d for byteCount %d." % (lineNum, len(line), 11+2*byteCount, byteCount))

        data = []
        for i in range(byteCount):
            hexPair = line[(9+2*i):(9+2*i+2)]
            byte = int(hexPair, 16)
            data.append(byte)

        checkSum = int(line[-2:], 16)
        records.append(HexRecord(type, data, checkSum, address))

    return records

def generatehexfile(inputlist, hexsubsettype=4):
    ''' From a sorted (by address) list of (address, binaryfilepath) tuples,
        produce a hex file string and return it. Assumes arguments are OK.
        Only hex subtype 4 is implemented.
    '''

    hexout = []

    if (hexsubsettype == 4):
        recordlength = 32
    elif (hexsubsettype == 2):
        recordlength = 16
    else:
        # not implemented
        return ''.join(hexout)

    # current address and segment address are carried between subfiles.
    curraddr = 0
    segaddr = 0
    for (addr, binfile) in inputlist:
        # open the file for processing
        with open(binfile, 'rb') as f:
            fsize = os.path.getsize(binfile)

            # set starting address.
            if addr >= (curraddr + segaddr):
                curraddr = addr - segaddr

            else:
                # shouldn't be out of order this way. error.
                raise UserWarning("Error: binfiles are out of order. Contact tool smith.")

            # work through the file generating & storing records as we go
            while f.tell() != fsize:
                # check if we need a new segment
                if (curraddr & 0xFFFF0000) != 0:
                    # set new segaddr
                    segaddr = (curraddr & 0xFFFF0000) + segaddr

                    if hexsubsettype == 4:
                        hexout.append(HexRecord(HEX_TYPE_EXT_LINEAR_ADDRESS, [(segaddr >> 24) & 0xFF, (segaddr >> 16) & 0xFF]).getRecord())
                    elif hexsubsettype == 2:
                        hexout.append(HexRecord(HEX_TYPE_EXT_SEG_ADDRESS, [(segaddr >> 12) & 0xFF, (segaddr >> 4) & 0xFF]).getRecord())
                    else:
                        raise UserWarning("Error: somehow hexsubsettype is broken, contact tool smith.")
                    # advance address pointer
                    curraddr = curraddr & 0x0000FFFF

                # read up to recordlength bytes from the file, don't bridge segment.
                if (curraddr + recordlength) > 0x10000:
                    bytestoread = (curraddr + recordlength) - 0x10000;
                else:
                    bytestoread = recordlength

                bindata = f.read(bytestoread)
                # bindata = struct.unpack('B'*len(bindata),bindata) # better to use ord actually
                bindata = [x for x in bindata]
                # bindata = map(ord, bindata)
                hexout.append(HexRecord(HEX_TYPE_DATA, bindata, address=curraddr).getRecord())
                curraddr += len(bindata)

    # add end of file record
    hexout.append(HexRecord(HEX_TYPE_EOF, []).getRecord())

    return hexout

def checkhextypearg(option, opt, value, parser):
    # check hex type argument
    if value not in HEX_ALLOWED_ADDRESS_TYPES:
        raise optparse.OptionValueError ("Error: HEX format subset type %d not acceptable."%value)

    setattr(parser.values, option.dest, value)

def commandline_split(option, opt, value, parser):
    # check the binary input
    binlist = value.split(',')
    if len(value.split(','))%2 != 0:
        raise optparse.OptionValueError("Error: each input binary must have a corresponding address")

    # convert to list of lists of (address, binfile)
    binlist = map(list, zip(*[iter(binlist)]*2))
    binlistout = []

    # make sure each argument in each pair is OK
    for [addr, binfile] in (binlist):
        # convert address to int. int() will raise any format errors
        rawaddr = addr
        if addr.find('0x') == 0:
            addr = int(addr, 16)
        else:
            addr = int(addr)
        if addr > 0xFFFFFFFF:
            raise optparse.OptionValueError("Error: address (%s, %s) exceeds 4gb."%(rawaddr, binfile))

        # ensure binfile path is ok, and abs it.
        if os.path.isfile(binfile):
            binfile = os.path.abspath(binfile)
        else:
            raise optparse.OptionValueError("Error: binfile path (%s, %s) is unacceptable"%(rawaddr, binfile))

        # save it to the output list as a tuple (unmodifiable after this), and
        # save the converted values to a list for examination later
        binlistout.append((addr, binfile))

    # now check if any file(size) + address will overlap another
    for i, binentry1 in enumerate(binlistout):
        for j, binentry2 in enumerate(binlistout):
            if (binentry1[0] < binentry2[0]) and (binentry1[0] + os.path.getsize(binentry1[1]) > binentry2[0]):
                raise optparse.OptionValueError("Error: binfile entry %s overlaps %s"%(str(binlist[i]), str(binlist[j])))

        # also check if addr + filesize is going to overflow 4gb limit
        if binentry1[0] + os.path.getsize(binentry1[1]) > (1<<32)-1:
            raise optparse.OptionValueError("Error: binfile entry %s exceeds 4gb limit"%(str(binlist[i])))

    # sort the output list (by address)
    binlistout.sort()

    setattr(parser.values, option.dest, binlistout)

def process_command_line(argv=None):
    '''
    Return a 2-tuple: (settings object, args list).
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    '''
    if argv is None:
        if len(sys.argv[1:]):
            argv = sys.argv[1:]
        else:
            argv = ['-h']

    # initialize the parser object:
    parser = optparse.OptionParser(
        formatter=optparse.TitledHelpFormatter(width=70),
        add_help_option=None)

    # define options here:
    parser.add_option('-r', '--format', dest='format', type="int",
                      default=4, action='callback', callback=checkhextypearg,
                      help='HEX format subtype. 0 is I8HEX, 2 is I16HEX, 4 is I32HEX. Default is %default. ONLY 2 AND 4 ACCEPTED RIGHT NOW.')
    parser.add_option('-b', '--binaries', dest='binaries', type='string',
                      default=None, action='callback', callback=commandline_split,
                      help='List of binary file inputs and start addresses. Addresses are either decimal or hex (must be prepended with 0x).', metavar='ADDRESS,FILE,ADDRESS,FILE,...')
    parser.add_option('-o', '--outfile', dest='outfile',
                      default=None,
                      help='Output file path, optional, defaults to first input binary file dot hex.', metavar='PATH')
    parser.add_option('-q', '--quiet',action="store_true", dest="quiet",
                      default=False,
                      help="Suppress non-critical output on stdout.")
    parser.add_option('-v', '--version',dest='version',
                      action="store_true",
                      default=False,
                      help='Print version and exit.')
    parser.add_option('-h', '--help', action='help',
                      help='Show this help message and exit.')

    settings, args = parser.parse_args(argv)

    # check number of arguments, verify values, etc.:
    if args:
        parser.error('error in arguments; '
                     '"%s" ignored.' % (args,))

    # further process settings & args if necessary

    return settings, args

if __name__ == "__main__":
    # set args and evaluate them
    # http://docs.python.org/2/library/optparse.html#optparse-extending-optparse
    settings,args = process_command_line()
    if settings.version:
        print ("bin2hex.py %s"%("0.1"))
        sys.exit(0)

    # make sure the selected hex record type can represent the largest address
    maxaddress = HEX_ALLOWED_ADDRESS_TYPES[settings.format]
    for (addr, binfile) in settings.binaries:
        # don't check filesize, if it's good enough for gnu objcopy it's ok for us.
        #if (addr + os.path.getsize(binfile)) > maxaddress:
            #print "Error, address+binfile size 0x%0X is too large for format!"%(addr + os.path.getsize(binfile))
        if addr > maxaddress:
            print ("Error, address size 0x%0X is too large for format!"%(addr))
            exit(errno.EINVAL)

    # check output file
    try:
        if settings.outfile is None:
            # set output file based on first input file.
            settings.outfile = os.path.splitext(settings.binaries[0][1])[0]+".hex"
            # raise ValueError("Output file must be set!")

        # now check the output file, make sure we can open it
        with open(settings.outfile, 'w') as f:
            pass
    except Exception as inst:
        print ("Error with output file: %s"%inst)
        sys.exit(errno.EINVAL)

    # now, produce the hex file from the input files and addresses
    hexfiledata = generatehexfile(settings.binaries, settings.format)

    # save it to the selected output file
    with open(settings.outfile, 'w') as f:
        f.write('\n'.join(hexfiledata))
        f.write('\n') # trailing newline

