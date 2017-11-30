#!/usr/bin/env python
# encoding: utf-8
"""
Mobi.py

Created by Elliot Kroo on 2009-12-25.
Copyright (c) 2009 Elliot Kroo. All rights reserved.
"""
from __future__ import absolute_import

import sys

from struct import calcsize, unpack

from .lz77 import uncompress_lz77
from . import utils


REC_DATA_OFF = 'Record Data Offset'
UNIQUE_ID = 'Unique ID'

PALMDOC = 'Palmdoc'
MOBI = 'Mobi'
EXTH = 'EXTH'

RECORDS = 'Records'
EXTRA_BYTES = 'Extra Bytes'
COMPRESSION = 'Compression'
IMAGE0 = 'First Image Index'
NONBOOK0 = 'First Non-Book Index'
FULLNAME = 'Full Name'
EXTH_FLAGS = 'EXTH Flags'
REC_COUNT = 'Record Count'
REC_ATTR = 'Record Attributes'

FLAG_HAS_EXTH = 0x40


class Mobi(object):
    def __init__(self, filename):
        try:
            if isinstance(filename, str):
                self.f = open(filename, "rb")
            else:
                self.f = filename
        except IOError as e:
            sys.stderr.write("Could not open %s! " % filename)
            raise e
        self.offset = 0
        self.parse()

    def parse(self):
        """ reads in the file, then parses record tables"""
        self.contents = utils.LazyContents(self.f)
        self.header = self.parseHeader()
        self.records = self.parseRecordInfoList()
        self.config = self.readRecord0()

    def read_record(self, recordnum, disable_compression=False):
        if self.config:
            roff = self.records[recordnum][REC_DATA_OFF]  # Record offset
            noff = self.records[recordnum+1][REC_DATA_OFF]  # Next offset

            if self.config[PALMDOC][COMPRESSION] == 1 or disable_compression:
                return self.contents[roff:noff]

            elif self.config[PALMDOC][COMPRESSION] == 2:
                xbytes = self.config[MOBI][EXTRA_BYTES]
                return uncompress_lz77(self.contents[roff:noff - xbytes])

    readRecord = read_record

    def read_image_record(self, imgnum):
        if self.config:
            rnum = self.config[MOBI][IMAGE0] + imgnum
            return self.readRecord(rnum, disable_compression=True)

    readImageRecord = read_image_record

    @property
    def author(self):
        "Returns the author of the book"
        return self.config[EXTH][RECORDS][100].decode('utf8')

    @property
    def title(self):
        "Returns the title of the book"
        return self.config[MOBI][FULLNAME].decode('utf8')

# ##########  Private API ###########################

    def __iter__(self):
        if not self.config:
            return

        for record in range(1, self.config[MOBI][NONBOOK0] - 1):
            yield self.readRecord(record)

    def parseRecordInfoList(self):
        records = {}
        hfmt = '>II'
        hlen = calcsize(hfmt)
        fields = [
            REC_DATA_OFF,
            UNIQUE_ID,
        ]

        # read in all records in info list
        for recordID in range(self.header[REC_COUNT]):
            # create tuple with info
            values = unpack(
                hfmt, self.contents[self.offset:self.offset + hlen])
            results = utils.toDict(zip(fields, values))

            # increment offset into file
            self.offset += hlen

            # futz around with the unique ID record, as the uniqueID's top 8
            # bytes are really the REC_ATTR:
            results[REC_ATTR] = (results[UNIQUE_ID] & 0xFF000000) >> 24
            results[UNIQUE_ID] = results[UNIQUE_ID] & 0x00FFFFFF

            # store into the records dict
            records[results[UNIQUE_ID]] = results

        return records

    def parseHeader(self):
        hfmt = '>32shhIIIIII4s4sIIH'
        hlen = calcsize(hfmt)
        fields = [
            "name",
            "attributes",
            "version",
            "created",
            "modified",
            "backup",
            "modnum",
            "appInfoId",
            "sortInfoID",
            "type",
            "creator",
            "uniqueIDseed",
            "nextRecordListID",
            REC_COUNT
        ]

        # unpack header, zip up into list of tuples
        values = unpack(hfmt, self.contents[self.offset:self.offset + hlen])
        results = utils.toDict(zip(fields, values))

        # increment offset into file
        self.offset += hlen

        return results

    def readRecord0(self):
        config = {
            PALMDOC: self.parsePalmDOCHeader(),
        }
        mobi = config[MOBI] = self.parseMobiHeader()
        if mobi[EXTH_FLAGS] & FLAG_HAS_EXTH != 0:
            config[EXTH] = self.parseEXTHHeader()
        else:
            config[EXTH] = None
        return config

    def parseEXTHHeader(self):
        hfmt = '>III'
        hlen = calcsize(hfmt)
        fields = [
            'identifier',
            'header length',
            REC_COUNT,
        ]

        # unpack header, zip up into list of tuples
        values = unpack(hfmt, self.contents[self.offset:self.offset + hlen])
        results = utils.toDict(zip(fields, values))

        self.offset += hlen

        results[RECORDS] = {}
        for record in range(results[REC_COUNT]):
            rtype, rlen = unpack(
                ">II", self.contents[self.offset:self.offset + 8])
            rdata = self.contents[self.offset + 8:self.offset + rlen]
            results[RECORDS][rtype] = rdata
            self.offset += rlen

        return results

    def parseMobiHeader(self):
        hfmt = '> IIII II 40s III IIIII IIII I 36s IIII 8s HHIIIII'
        hlen = calcsize(hfmt)
        fields = [
            "identifier",
            "header length",
            "Mobi type",
            "text Encoding",

            "Unique-ID",
            "Generator version",

            "-Reserved",

            NONBOOK0,
            "Full Name Offset",
            "Full Name Length",

            "Language",
            "Input Language",
            "Output Language",
            "Format version",
            IMAGE0,

            "First Huff Record",
            "Huff Record Count",
            "First DATP Record",
            "DATP Record Count",

            EXTH_FLAGS,

            "-36 unknown bytes, if Mobi is long enough",

            "DRM Offset",
            "DRM Count",
            "DRM Size",
            "DRM Flags",

            "-Usually Zeros, unknown 8 bytes",

            "-Unknown",
            "Last Image Record",
            "-Unknown",
            "FCIS record",
            "-Unknown",
            "FLIS record",
            "Unknown"
        ]

        # unpack header, zip up into list of tuples
        values = unpack(hfmt, self.contents[self.offset:self.offset + hlen])
        results = utils.toDict(zip(fields, values))

        results['Start Offset'] = self.offset

        results[FULLNAME] = (self.contents[
          self.records[0][REC_DATA_OFF] + results['Full Name Offset']:
          self.records[0][REC_DATA_OFF] + results['Full Name Offset'] +
          results['Full Name Length']])

        results['Has DRM'] = results['DRM Offset'] != 0xFFFFFFFF

        self.offset += results['header length']

        def onebits(x, width=16):
            return len(list(filter(lambda x: x == "1",
                                   (str((x >> i) & 1)
                                    for i in range(width - 1, -1, -1)))))

        results[EXTRA_BYTES] = \
            2 * onebits(unpack(">H", self.contents[self.offset-2:self.offset])[0]
                        & 0xFFFE)

        return results

    def parsePalmDOCHeader(self):
        hfmt = '>HHIHHHH'
        hlen = calcsize(hfmt)
        fields = [
            COMPRESSION,
            "Unused",
            "text length",
            "record count",
            "record size",
            "Encryption Type",
            "Unknown"
        ]
        offset = self.records[0][REC_DATA_OFF]
        # create tuple with info
        values = unpack(hfmt, self.contents[offset:offset + hlen])
        results = utils.toDict(zip(fields, values))

        self.offset = offset + hlen

        return results
