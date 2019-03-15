# distutils: language=c++
"""Python bindings for C++ srchilite"""
from libcpp.map cimport map as std_map
from libcpp.set cimport set as std_set
from libcpp.string cimport string as std_string
from libcpp.utility cimport pair as std_pair
from libcpp cimport bool as cpp_bool

from cython.operator cimport dereference as deref

from srchilite cimport cpp_srchilite
from srchilite cimport bindings

import os
from collections import ChainMap
from collections.abc import Mapping, Sequence, Hashable, MutableSequence


#
# converters
#
cdef std_string str_to_cpp(object x):
    cdef std_string s
    x = x.encode()
    s = std_string(<const char*> x)
    return s


cdef object std_string_to_py(std_string x):
    pyx = x.c_str()
    pyx = pyx.decode()
    return pyx


#
# Binding classes & functions
#


cdef class _LangMap:

    def __cinit__(self, object filename="lang.map", object path=None):
        cdef std_string cpp_path
        cdef std_string cpp_filename = str_to_cpp(filename)
        if path is None:
            self.path, self.filename = os.path.split(os.path.abspath(filename))
            self.abspath = os.path.abspath(filename)
            self.ptx = new cpp_srchilite.LangMap(cpp_filename)
        else:
            self.path = os.path.abspath(path)
            self.filename = filename
            self.abspath = os.path.join(path, filename)
            cpp_path = str_to_cpp(path)
            self.ptx = new cpp_srchilite.LangMap(cpp_path, cpp_filename)
        # open if we can
        if os.path.exists(self.abspath):
            self.ptx.open()

    def __dealloc__(self):
        del self.ptx

    def __iter__(self):
        cdef std_string cpp_lang
        cdef std_set[std_string] cpp_lang_names = self.ptx.getLangNames()
        for cpp_lang in cpp_lang_names:
            lang = std_string_to_py(cpp_lang)
            yield lang

    def __len__(self):
        return self.ptx.getLangNames().size()

    def __getitem__(self, key):
        cdef std_string cpp_key = str_to_cpp(key)
        cdef std_string cpp_value = self.ptx.getMappedFileName(cpp_key)
        value = std_string_to_py(cpp_value)
        value = os.path.join(self.path, value)
        return value

    def open(self):
        """Opens the file if we can"""
        self.ptx.open()

    def print(self):
        self.ptx.print()


class LangMap(_LangMap, Mapping):
    """A LangMap object based on the passed map file (using the specified
    path.

    Parameters
    ----------
    filename : str, optional
        The map file.  Defaults to "lang.map"
    path : str, optional
        The path where to search for the filename
    """



def retrieve_data_dir(bint reload=False):
    """Gets the data dir set by the $SOURCE_HIGHLIGHT_DATADIR,
    in the configuration file (~/.source-highlight/source-highlight.conf),
    or hard-coded into the library ($PREFIX/share/source-highlight).
    """
    cdef cpp_srchilite.Settings settings = cpp_srchilite.Settings()
    cdef std_string cpp_rtn = settings.retrieveDataDir(reload)
    rtn = std_string_to_py(cpp_rtn)
    return rtn

#
# API functions
#
class _TokenType(Sequence, Hashable):
    # Originally forked from Pygments
    # Copyright (c) 2006-2017 by the respective authors (see AUTHORS file).
    # All rights reserved.
    parent = None

    def __init__(self, val=()):
        self.val = val
        self._name = "Token"
        if val:
            self._name += "." + ".".join(val)
        self.subtypes = set()
        self._subtype_map = {}

    def __getitem__(self, key):
        return self.val[key]

    def __len__(self):
        return len(self.val)

    def __contains__(self, item):
        return self is item or (
            type(item) is self.__class__ and
            item[:len(self)] == self
        )

    def __getattr__(self, name):
        spec = self.val + (name,)
        if spec in self._subtype_map:
            return self._subtype_map[spec]
        new = _TokenType(spec)
        new.parent = self
        self.subtypes.add(new)
        self._subtype_map[spec] = new
        return new

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)

    def __copy__(self):
        # These instances are supposed to be singletons
        return self

    def __deepcopy__(self, memo):
        # These instances are supposed to be singletons
        return self

    def __hash__(self):
        return hash(self.val)

    def split(self):
        buf = []
        node = self
        while node is not None:
            buf.append(node)
            node = node.parent
        buf.reverse()
        return buf


Token = _TokenType()


cdef dict _STRING_TO_TOKEN_CACHE = {"": Token}


def string_to_token(str s):
    """Convert a string into a token. For example, "String.Double"
    becomes Token.Literal.String.Double. The empty string becomes Token.
    """
    # Originally forked from Pygments
    # Copyright (c) 2006-2017 by the respective authors (see AUTHORS file).
    # All rights reserved.
    if s in _STRING_TO_TOKEN_CACHE:
        return _STRING_TO_TOKEN_CACHE[s]
    if len(s) == 0:
        return Token
    node = Token
    for item in s.split('.'):
        node = getattr(node, item)
    _STRING_TO_TOKEN_CACHE[s] = node
    return node


# Here for Pygements API compatibility
string_to_tokentype = string_to_token


def get_tokens(str code, str lang="", str filename="", object path=None):
    """Returns token list from code in a give language
    """
    cdef std_string cpp_code = str_to_cpp(code)
    cdef std_string cpp_filename
    cdef std_string cpp_path
    cdef cpp_srchilite.TokenPairsPtr cpp_tokens
    cdef cpp_srchilite.TokenPair cpp_token
    if lang:
        path, filename = os.path.split(LANG_MAP_CACHE[lang])
    elif not filename:
        raise ValueError("Either 'lang' or 'filename' must be given "
                         "and non-empty")
    elif path is None:
        path, filename = os.path.split(filename)
    cpp_filename = str_to_cpp(filename)
    cpp_path = str_to_cpp(path)
    cpp_tokens = cpp_srchilite.get_tokens(cpp_code, cpp_path, cpp_filename)
    tokens = []
    for cpp_token in deref(cpp_tokens):
        first = std_string_to_py(cpp_token.first)
        token = string_to_token(first)
        second = std_string_to_py(cpp_token.second)
        tokens.append((token, second))
    return tokens
#
# Custom API
#

class _LangMapCache(ChainMap):
    """Unified look-up for muliple. The initial empty dictionary is
    a trap that catches user settings. The lang_map items here are kept
    in-sync below by PY_SOURCE_HIGHLIGHT_PATH
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._trap = {}
        self.maps = [self._trap]
        self.reset_maps()

    def clear(self):
        """Removes all map entries"""
        self._trap.clear()
        self.reset_maps()

    def reset_maps(self):
        """Resets the maps to the current PY_SOURCE_HIGHLIGHT_PATH"""
        global PY_SOURCE_HIGHLIGHT_PATH
        prev = {m.abspath: m for m in self.maps[1:]}
        maps = [self._trap]
        for p in PY_SOURCE_HIGHLIGHT_PATH:
            # get the abspath of the lang map
            p = os.path.abspath(p)
            if ".map" == os.path.splitext(p)[1] or os.path.isfile(p):
                pass
            else:
                p = os.path.join(p, "lang.map")
            # re-add LangMap if it exists, make a new one if it doesn't
            if p in prev:
                maps.append(prev[p])
            else:
                maps.append(LangMap(filename=p))
        self.maps = maps


class _PySourceHighlightPath(MutableSequence):
    """A custom list-like for handling $PY_SOURCE_HIGHLIGHT_PATH"""

    def __init__(self, *args):
        if args:
            self._list = args
        elif "PY_SOURCE_HIGHLIGHT_PATH" in os.environ:
            self._list = os.environ["PY_SOURCE_HIGHLIGHT_PATH"].split(os.pathsep)
        else:
            self._list = [retrieve_data_dir()]

    def __getitem__(self, item):
        return self._list[item]

    def __setitem__(self, item, value):
        global LANG_MAP_CACHE
        self._list[item] = value
        LANG_MAP_CACHE.reset_maps()

    def __delitem__(self, item):
        global LANG_MAP_CACHE
        del self._list[item]
        LANG_MAP_CACHE.reset_maps()

    def __len__(self):
        return len(self._list)

    def insert(self, i, item):
        global LANG_MAP_CACHE
        self._list.insert(i, item)
        LANG_MAP_CACHE.reset_maps()

    def __copy__(self):
        # supposed to be singleton
        return self

    def __deepcopy__(self, memo):
        # supposed to be singleton
        return self


# We have to initialize in this order
PY_SOURCE_HIGHLIGHT_PATH = _PySourceHighlightPath()
LANG_MAP_CACHE = _LangMapCache()
