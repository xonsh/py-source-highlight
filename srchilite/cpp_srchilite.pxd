# distutils: language=c++
"""Bindings to the C++ library for srchilite"""
from libcpp.map cimport map as std_map
from libcpp.set cimport set as std_set
from libcpp.string cimport string as std_string


cdef extern from "srchilite/highlightrulefactory.h" namespace "srchilite":
    cdef cppclass HighlightRuleFactory:
        HighlightRuleFactory()


cdef extern from "srchilite/regexrulefactory.h" namespace "srchilite":
    cdef cppclass RegexRuleFactory(HighlightRuleFactory):
        RegexRuleFactory()


cdef extern from "srchilite/langdefmanager.h" namespace "srchilite":
    cdef cppclass LangDefManager:
        LangDefManager(HighlightRuleFactory*)


cdef extern from "srchilite/langmap.h" namespace "srchilite":
    cdef cppclass LangMap:
        LangMap(const std_string&)
        LangMap(const std_string&, const std_string&)
        void print()
        void open()
        std_map[std_string, std_string].const_iterator begin()
        std_map[std_string, std_string].const_iterator end()
        const std_string getFileName(const std_string&)
        const std_string getMappedFileName(const std_string)
        const std_string getMappedFileNameFromFileName(const std_string&)
        std_set[std_string] getLangNames()
        std_set[std_string] getMappedFileNames()
        void reload(const std_string&, const std_string&)
