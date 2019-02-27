# distutils: language=c++
"""Python bindings for C++ srchilite"""
from libcpp.string cimport string as std_string

from srchilite cimport cpp_srchilite
from srchilite cimport bindings


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

    def __cinit__(self, object filename, object path=None):
        cdef std_string cpp_path
        cdef std_string cpp_filename = str_to_cpp(filename)
        if path is None:
            self.ptx = new cpp_srchilite.LangMap(cpp_filename)
        else:
            cpp_path = str_to_cpp(path)
            self.ptx = new cpp_srchilite.LangMap(cpp_path, cpp_filename)

    def __dealloc__(self):
        del self.ptx

    def print(self):
        self.ptx.print()


class LangMap(_LangMap):
    """A LangMap object based on the passed map file (using the specified
    path.

    Parameters
    ----------
    filename : str
        The map file
    path : str, optional
        The path where to search for the filename
    """
