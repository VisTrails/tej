"""Utility functions.
"""

from __future__ import unicode_literals

import sys


PY3 = sys.version_info[0] == 3


if PY3:
    izip = zip
    irange = range
    iteritems = dict.items
    itervalues = dict.values
    listvalues = lambda d: list(d.values())
else:
    import itertools
    izip = itertools.izip
    irange = xrange
    iteritems = dict.iteritems
    itervalues = dict.itervalues
    listvalues = dict.values


if PY3:
    unicode_ = str
else:
    unicode_ = unicode
