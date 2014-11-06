# The MIT License (MIT)
#
# Copyright (c) 2014 Philippe Proulx <philippe.proulx@efficios.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import collections
import enum


@enum.unique
class ByteOrder(enum.Enum):
    NATIVE = 0
    LE = 1
    BE = 2


@enum.unique
class Encoding(enum.Enum):
    NONE = 0
    UTF8 = 1
    ASCII = 2


class Integer:
    def __init__(self):
        self._signed = False
        self._byte_order = ByteOrder.NATIVE
        self._base = 10
        self._encoding = Encoding.NONE
        self._align = 1
        self._map = None
        self._size = None

    @property
    def signed(self):
        return self._signed

    @signed.setter
    def signed(self, value):
        self._signed = value

    @property
    def byte_order(self):
        return self._byte_order

    @byte_order.setter
    def byte_order(self, value):
        self._byte_order = value

    @property
    def base(self):
        return self._base

    @base.setter
    def base(self, value):
        self._base = value

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        self._encoding = value

    @property
    def align(self):
        return self._align

    @align.setter
    def align(self, value):
        self._align = value

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = value

    @property
    def map(self):
        return self._map

    @map.setter
    def map(self, value):
        self._map = value


class FloatingPoint:
    def __init__(self):
        self._exp_dig = None
        self._mant_dig = None
        self._align = 1
        self._byte_order = ByteOrder.NATIVE

    @property
    def exp_dig(self):
        return self._exp_dig

    @exp_dig.setter
    def exp_dig(self, value):
        self._exp_dig = value

    @property
    def mant_dig(self):
        return self._mant_dig

    @mant_dig.setter
    def mant_dig(self, value):
        self._mant_dig = value

    @property
    def byte_order(self):
        return self._byte_order

    @byte_order.setter
    def byte_order(self, value):
        self._byte_order = value

    @property
    def align(self):
        return self._align

    @align.setter
    def align(self, value):
        self._align = value


class Enum:
    def __init__(self):
        self._labels = collections.OrderedDict()

    @property
    def integer(self):
        return self._integer

    @integer.setter
    def integer(self, value):
        self._integer = value

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, value):
        self._labels = value

    def value_of(self, label):
        return self._labels[label]

    def label_of(self, value):
        for label, vrange in self._labels.items():
            if value >= vrange[0] and value <= vrange[1]:
                return label

    def __getitem__(self, key):
        if type(key) is str:
            return self.value_of(key)
        elif type(key) is int:
            return self.label_of(key)

        raise TypeError('wrong subscript type')


class String:
    def __init__(self):
        self._encoding = Encoding.NONE

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        self._encoding = value


class _ArraySequence:
    def __init__(self):
        pass

    @property
    def element(self):
        return self._element

    @element.setter
    def element(self, value):
        self._element = value

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        self._length = value


class Array(_ArraySequence):
    pass


class Sequence(_ArraySequence):
    pass


class _StructVariant:
    def __init__(self):
        self._fields = collections.OrderedDict()

    @property
    def fields(self):
        return self._fields

    def __getitem__(self, key):
        return self.fields[key]


class Struct(_StructVariant):
    def __init__(self):
        self._align = None
        super().__init__()

    @property
    def align(self):
        return self._align

    @align.setter
    def align(self, value):
        self._align = value


class Variant(_StructVariant):
    def __init__(self):
        self._tag = None
        super().__init__()

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, value):
        self._tag = value


class Trace:
    def __init__(self):
        self._major = None
        self._minor = None
        self._uuid = None
        self._byte_order = None
        self._packet_header = None

    @property
    def major(self):
        return self._major

    @major.setter
    def major(self, value):
        self._major = value

    @property
    def minor(self):
        return self._minor

    @minor.setter
    def minor(self, value):
        self._minor = value

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = value

    @property
    def byte_order(self):
        return self._byte_order

    @byte_order.setter
    def byte_order(self, value):
        self._byte_order = value

    @property
    def packet_header(self):
        return self._packet_header

    @packet_header.setter
    def packet_header(self, value):
        self._packet_header = value


class Env(dict):
    pass


class Clock:
    def __init__(self):
        self._name = None
        self._uuid = None
        self._description = None
        self._freq = None
        self._precision = None
        self._offset_s = None
        self._offset = None
        self._absolute = False

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value):
        self._uuid = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def precision(self):
        return self._precision

    @property
    def freq(self):
        return self._freq

    @freq.setter
    def freq(self, value):
        self._freq = value

    @precision.setter
    def precision(self, value):
        self._precision = value

    @property
    def offset_s(self):
        return self._offset_s

    @offset_s.setter
    def offset_s(self, value):
        self._offset_s = value

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value

    @property
    def absolute(self):
        return self._absolute

    @absolute.setter
    def absolute(self, value):
        self._absolute = value


class Event:
    def __init__(self):
        self._id = None
        self._name = None
        self._loglevel = None
        self._context = None
        self._fields = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def loglevel(self):
        return self._loglevel

    @loglevel.setter
    def loglevel(self, value):
        self._loglevel = value

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, value):
        self._context = value

    @property
    def fields(self):
        return self._fields

    @fields.setter
    def fields(self, value):
        self._fields = value

    def __getitem__(self, key):
        if type(self.fields) is _StructVariant:
            return self.fields[key]

        raise TypeError('{} is not subscriptable')


class Stream:
    def __init__(self):
        self._id = 0
        self._packet_context = None
        self._event_header = None
        self._event_context = None
        self._events = []

    def init_events_dict(self):
        self._events_dict = {}

        for ev in self._events:
            self._events_dict[ev.id] = ev
            self._events_dict[ev.name] = ev

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def packet_context(self):
        return self._packet_context

    @packet_context.setter
    def packet_context(self, value):
        self._packet_context = value

    @property
    def event_header(self):
        return self._event_header

    @event_header.setter
    def event_header(self, value):
        self._event_header = value

    @property
    def event_context(self):
        return self._event_context

    @event_context.setter
    def event_context(self, value):
        self._event_context = value

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, value):
        self._events = value

    def get_event(self, idname):
        return self._events_dict[idname]


class Doc:
    def __init__(self):
        self._trace = None
        self._env = None
        self._clocks = collections.OrderedDict()
        self._streams = collections.OrderedDict()

    @property
    def trace(self):
        return self._trace

    @trace.setter
    def trace(self, value):
        self._trace = value

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, value):
        self._env = value

    @property
    def clocks(self):
        return self._clocks

    @clocks.setter
    def clocks(self, value):
        self._clocks = value

    @property
    def streams(self):
        return self._streams

    @streams.setter
    def streams(self, value):
        self._streams = value
