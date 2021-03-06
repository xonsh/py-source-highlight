# distutils: language=c++
"""Python bindings for C++ srchilite"""
from libcpp.string cimport string as std_string

from srchilite cimport cpp_srchilite

#
# Type conversions
#
cdef std_string str_to_cpp(object x)
cdef object std_string_to_py(std_string x)


cdef class _LangMap:
    cdef cpp_srchilite.LangMap * ptx
