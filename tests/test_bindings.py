"""Tests basic bindings"""
import os

from srchilite.bindings import retrieve_data_dir


def test_retrieve_data_dir():
    rtn = retrieve_data_dir()
    assert len(rtn) > 0
    assert 'lang.map' in os.listdir(rtn)