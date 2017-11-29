#!/usr/bin/env python
# encoding: utf-8
"""
utils.py

Created by Elliot Kroo on 2009-12-25.
Copyright (c) 2009 Elliot Kroo. All rights reserved.
"""


class LazyContents:
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


def toDict(tuples):
    resultsDict = {}
    for field, value in tuples:
        if len(field) > 0 and field[0] != "-":
            resultsDict[field] = value
    return resultsDict
