"""Tests basic bindings"""
import os

from srchilite.bindings import retrieve_data_dir, LANG_MAP_CACHE


def test_retrieve_data_dir():
    rtn = retrieve_data_dir()
    assert len(rtn) > 0
    assert 'lang.map' in os.listdir(rtn)


def test_lang_map_cache():
    py = LANG_MAP_CACHE['py']
    assert os.path.isabs(py)
    assert 'py' in py
    assert '.lang' == os.path.splitext(py)[1]