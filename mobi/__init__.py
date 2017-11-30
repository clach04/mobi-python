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

FLAG_HAS_EXTH = 0x40


class Mobi:
    def parse(self):
        """ reads in the file, then parses record tables"""
        self.contents = utils.LazyContents(self.f)
        self.header = self.parseHeader()
        self.records = self.parseRecordInfoList()
        self.readRecord0()

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

    def __iter__(self):
        if not self.config:
            return

        for record in range(1, self.config[MOBI][NONBOOK0] - 1):
            yield self.readRecord(record)

    def parseRecordInfoList(self):
        records = {}
        # read in all records in info list
        for recordID in range(self.header['number of records']):
            headerfmt = '>II'
            headerlen = calcsize(headerfmt)
            fields = [
                REC_DATA_OFF,
                UNIQUE_ID,
            ]
            # create tuple with info
            results = zip(fields, unpack(headerfmt, self.contents[self.offset:self.offset+headerlen]))

            # increment offset into file
            self.offset += headerlen

            # convert tuple to dictionary
            resultsDict = utils.toDict(results)

            # futz around with the unique ID record, as the uniqueID's top 8 bytes are
            # really the "record attributes":
            resultsDict['record Attributes'] = (resultsDict[UNIQUE_ID] & 0xFF000000) >> 24
            resultsDict[UNIQUE_ID] = resultsDict[UNIQUE_ID] & 0x00FFFFFF

            # store into the records dict
            records[resultsDict[UNIQUE_ID]] = resultsDict

        return records

    def parseHeader(self):
        headerfmt = '>32shhIIIIII4s4sIIH'
        headerlen = calcsize(headerfmt)
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
            "number of records"
        ]

        # unpack header, zip up into list of tuples
        results = zip(fields, unpack(headerfmt, self.contents[self.offset:self.offset+headerlen]))

        # increment offset into file
        self.offset += headerlen

        # convert tuple array to dictionary
        resultsDict = utils.toDict(results)

        return resultsDict

    def readRecord0(self):
        self.config = {
            PALMDOC: self.parsePalmDOCHeader(),
        }
        mobi = self.config[MOBI] = self.parseMobiHeader()
        if mobi[EXTH_FLAGS] & FLAG_HAS_EXTH != 0:
            self.config[EXTH] = self.parseEXTHHeader()
        else:
            self.config[EXTH] = None

    def parseEXTHHeader(self):
        headerfmt = '>III'
        headerlen = calcsize(headerfmt)

        fields = [
            'identifier',
            'header length',
            'record Count'
        ]

        # unpack header, zip up into list of tuples
        results = zip(fields, unpack(headerfmt, self.contents[self.offset:self.offset+headerlen]))

        # convert tuple array to dictionary
        resultsDict = utils.toDict(results)

        self.offset += headerlen
        resultsDict[RECORDS] = {}
        for record in range(resultsDict['record Count']):
            recordType, recordLen = unpack(">II", self.contents[self.offset:self.offset+8])
            recordData = self.contents[self.offset+8:self.offset+recordLen]
            resultsDict[RECORDS][recordType] = recordData
            self.offset += recordLen

        return resultsDict

    def parseMobiHeader(self):
        headerfmt = '> IIII II 40s III IIIII IIII I 36s IIII 8s HHIIIII'
        headerlen = calcsize(headerfmt)

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
        results = zip(fields,
                      unpack(headerfmt,
                             self.contents[self.offset:self.offset + headerlen]))

        # convert tuple array to dictionary
        resultsDict = utils.toDict(results)

        resultsDict['Start Offset'] = self.offset

        resultsDict[FULLNAME] = (self.contents[
          self.records[0][REC_DATA_OFF] + resultsDict['Full Name Offset']:
          self.records[0][REC_DATA_OFF] + resultsDict['Full Name Offset'] +
          resultsDict['Full Name Length']])

        resultsDict['Has DRM'] = resultsDict['DRM Offset'] != 0xFFFFFFFF

        self.offset += resultsDict['header length']

        def onebits(x, width=16):
            return len(list(filter(lambda x: x == "1",
                                   (str((x >> i) & 1)
                                    for i in range(width - 1, -1, -1)))))

        resultsDict[EXTRA_BYTES] = \
            2 * onebits(unpack(">H", self.contents[self.offset-2:self.offset])[0]
                        & 0xFFFE)

        return resultsDict

    def parsePalmDOCHeader(self):
        headerfmt = '>HHIHHHH'
        headerlen = calcsize(headerfmt)
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
        results = zip(fields,
                      unpack(headerfmt,
                             self.contents[offset:offset + headerlen]))

        # convert tuple array to dictionary
        resultsDict = utils.toDict(results)

        self.offset = offset+headerlen
        return resultsDict
