#!/usr/bin/env python
# encoding: utf-8
"""
Mobi.py

Created by Elliot Kroo on 2009-12-25.
Copyright (c) 2009 Elliot Kroo. All rights reserved.
"""

from __future__ import absolute_import

import sys
import logging

from struct import calcsize, unpack

from six import string_types

from .lz77 import uncompress_lz77


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

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
FULLNAME_OFF = 'Full Name Offset'
FULLNAME_LEN = 'Full Name Length'
EXTH_FLAGS = 'EXTH Flags'
REC_COUNT = 'Record Count'
REC_ATTR = 'Record Attributes'
DRM_OFFSET = 'DRM Offset'
DRM_OFFSET_MAX = 0xFFFFFFFF

UNKNOWN = 'Unknown'
UNUSED = 'Unused'

FLAG_HAS_EXTH = 0x40


class LazyContents(object):
    """ read contents without loading the whole file in memory """

    def __init__(self, file):
        self.f = file

    def __getitem__(self, target):
        if isinstance(target, slice):
            assert target.step is None, "step %d not implemented" % target.step
            start = target.start
            length = target.stop - start
        else:
            start = int(target)
            length = 1
        self.f.seek(start)
        return self.f.read(length)


class Mobi(object):
    def __init__(self, path_or_file):
        if isinstance(path_or_file, string_types):
            self.f = open(path_or_file, "rb")
        else:
            assert hasattr(path_or_file, 'read'), \
                'Pass a path or file-like object'
            self.f = path_or_file

        self.has_drm = False
        self.offset = 0
        self.parse()

    def close(self):
        if self.f is None:
            return

        self.f.close()
        self.f = None

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def parse(self):
        """ reads in the file, then parses record tables"""
        self.contents = LazyContents(self.f)
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
            results = dict(zip(fields, values))

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
        results = dict(zip(fields, values))

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
        results = dict(zip(fields, values))

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

            DRM_OFFSET,
            "DRM Count",
            "DRM Size",
            "DRM Flags",

            "-Usually Zeros, unknown 8 bytes",

            UNKNOWN,
            "Last Image Record",
            UNKNOWN,
            "FCIS record",
            UNKNOWN,
            "FLIS record",
            UNKNOWN
        ]

        # unpack header, zip up into list of tuples
        values = unpack(hfmt, self.contents[self.offset:self.offset + hlen])
        results = dict(zip(fields, values))

        LOGGER.debug('Starting offset: %i', self.offset)

        offset = self.records[0][REC_DATA_OFF] + results[FULLNAME_OFF]
        results[FULLNAME] = \
            self.contents[offset:offset + results[FULLNAME_LEN]]

        self.has_drm = results[DRM_OFFSET] != DRM_OFFSET_MAX
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
            UNUSED,
            "text length",
            "record count",
            "record size",
            "Encryption Type",
            UNKNOWN
        ]
        offset = self.records[0][REC_DATA_OFF]
        # create tuple with info
        values = unpack(hfmt, self.contents[offset:offset + hlen])
        results = dict(zip(fields, values))

        self.offset = offset + hlen

        return results
