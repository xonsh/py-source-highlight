# distutils: language=c++
"""Bindings to the C++ library for srchilite"""
from libcpp.map cimport map as std_map
from libcpp.set cimport set as std_set
from libcpp.string cimport string as std_string
from libcpp.vector cimport vector as std_vector
from libcpp.utility cimport pair as std_pair
from libcpp cimport bool as cpp_bool
from libc.stdint cimport uint32_t

#
# boost shared pointers
#
cdef extern from "boost/shared_ptr.hpp" namespace "boost":

    cdef cppclass shared_ptr[T]:
        shared_ptr()
        shared_ptr(T*)
        T* get()
        T& operator*()
        cpp_bool unique()
        long use_count()
        swap(shared_ptr&)

    shared_ptr[T] reinterpret_pointer_cast[T,U](shared_ptr[U])


#
# Actual src-hilite library
#

cdef extern from "srchilite/highlightrulefactory.h" namespace "srchilite":
    cdef cppclass HighlightRuleFactory:
        HighlightRuleFactory()


cdef extern from "srchilite/regexrulefactory.h" namespace "srchilite":
    cdef cppclass RegexRuleFactory(HighlightRuleFactory):
        RegexRuleFactory()


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


cdef extern from "srchilite/highlightstate.h" namespace "srchilite":
    cdef cppclass HighlightState:
        HighlightState()
        HighlightState(const std_string)

    ctypedef shared_ptr[HighlightState] HighlightStatePtr


cdef extern from "srchilite/langdefmanager.h" namespace "srchilite":
    cdef cppclass LangDefManager:
        LangDefManager(HighlightRuleFactory*)
        HighlightStatePtr getHighlightState(const std_string&)
        HighlightStatePtr getHighlightState(const std_string&, const std_string&)


cdef extern from "srchilite/formatterparams.h" namespace "srchilite":
    cdef cppclass FormatterParams:
        FormatterParams(const std_string&)
        std_string fileNameNoPath
        int start
        std_string filename
        uint32_t line


cdef extern from "srchilite/formatter.h" namespace "srchilite":
    cdef cppclass Formatter:
        Formatter()
        void format(const std_string&, const FormatterParams*)

    ctypedef shared_ptr[Formatter] FormatterPtr


cdef extern from "srchilite/formattermanager.h" namespace "srchilite":
    cdef cppclass FormatterManager:
        FormatterManager(FormatterPtr)


cdef extern from "srchilite/sourcehighlighter.h" namespace "srchilite":
    cdef cppclass SourceHighlighter:
        SourceHighlighter(HighlightStatePtr)
        void highlightParagraph(const std_string&)
        void setFormatterParams(FormatterParams*)
        void setFormatterManager(const FormatterManager*)

#
# Helper classes
#

cdef extern from "helpers.hpp" namespace "pysrchilite":

    ctypedef shared_ptr[std_vector[std_pair[std_string, std_string]]] GetTokensPtr

    cdef cppclass LexerGetTokensFormatter:
        LexerGetTokensFormatter(const std_string, GetTokensPtr)

    ctypedef shared_ptr[LexerGetTokensFormatter] LexerGetTokensFormatterPtr

    GetTokensPtr get_tokens(const std_string, const std_string path,
                            const std_string file)