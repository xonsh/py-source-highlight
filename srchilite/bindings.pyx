# distutils: language=c++
"""Python bindings for C++ srchilite"""
from libcpp.map cimport map as std_map
from libcpp.set cimport set as std_set
from libcpp.string cimport string as std_string
from libcpp.utility cimport pair as std_pair

from cython.operator cimport dereference as deref

from srchilite cimport cpp_srchilite
from srchilite cimport bindings

import os
from collections.abc import Mapping, Sequence



#
# converters
#
cdef std_string str_to_cpp(object x):
    cdef std_string s
    x = x.encode()
    s = std_string(<const char*> x)
    return s


cdef object std_string_to_py(std_string x):
    pyx = x
    pyx = pyx.decode()
    return pyx


#
# Binding classes
#


cdef class _LangMap:

    def __cinit__(self, object filename="lang.map", object path=None):
        cdef std_string cpp_path
        cdef std_string cpp_filename = str_to_cpp(filename)
        if path is None:
            self.ptx = new cpp_srchilite.LangMap(cpp_filename)
        else:
            cpp_path = str_to_cpp(path)
            self.ptx = new cpp_srchilite.LangMap(cpp_path, cpp_filename)
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
        return value

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

#
# API functions
#
class _TokenType(Sequence):
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
        #if not name or not name[0].isupper():
        #    return tuple.__getattribute__(self, name)
        new = _TokenType(self.val + (name,))
        self.subtypes.add(new)
        #setattr(self, val, new)
        new.parent = self
        return new

    def __repr__(self):
        return 'Token' + (self and '.' or '') + '.'.join(self)

    def __copy__(self):
        # These instances are supposed to be singletons
        return self

    def __deepcopy__(self, memo):
        # These instances are supposed to be singletons
        return self

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


def get_tokens(str code, str filename, object path=None):
    """Returns token list from code in a give language
    """
    cdef std_string cpp_code = str_to_cpp(code)
    cdef std_string cpp_filename
    cdef std_string cpp_path
    cdef cpp_srchilite.TokenPairsPtr cpp_tokens
    cdef cpp_srchilite.TokenPair cpp_token
    if path is None:
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
# Mostly Pygments compatible API
#
