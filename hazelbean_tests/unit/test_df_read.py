"""Tests for df_read's input handling and its encoding fallbacks.

The fallbacks were unreachable: each `raise NameError` sat after the inner try/except rather than
inside it, so a file that failed the first read raised even when a later encoding would have read
it. These pin that the cascade now reaches a result, and that a pathlib.Path is accepted.
"""
import os
from pathlib import Path

import pandas as pd
import pytest

import hazelbean as hb


def test_a_latin1_file_is_read_by_the_fallback_rather_than_raising(tmp_path):
    # 0xE9 is e-acute in latin1 and invalid utf-8, so pandas' default read fails and one of the
    # single-byte fallbacks has to carry it. International datasets arrive like this routinely.
    path = tmp_path / 'latin1.csv'
    path.write_bytes('country,value\nQu\xe9bec,1\n'.encode('latin1'))

    with pytest.raises(UnicodeDecodeError):
        pd.read_csv(path)                      # the default alone cannot read it

    df = hb.df_read(str(path))
    assert list(df.columns) == ['country', 'value']
    assert len(df) == 1


def test_a_utf8_file_with_a_byte_order_mark_keeps_a_clean_first_column(tmp_path):
    # Excel writes the BOM, and read without allowing for it the first column name arrives with a
    # zero-width character glued to the front, which then fails every later lookup by name.
    path = tmp_path / 'bom.csv'
    path.write_bytes('﻿iso3,value\nFRA,1\n'.encode('utf-8'))
    assert hb.df_read(str(path)).columns[0] == 'iso3'


def test_a_path_object_is_accepted(tmp_path):
    # Callers that build paths with pathlib should not have to str() them at every call site.
    path = tmp_path / 'plain.csv'
    pd.DataFrame({'a': [1, 2]}).to_csv(path, index=False)
    assert len(hb.df_read(Path(path))) == 2
    assert len(hb.df_read(str(path))) == 2


def test_a_dataframe_passes_straight_through(tmp_path):
    # The lazy-loading convention: a caller may hold either a path or an already-loaded frame.
    df = pd.DataFrame({'x': [1, 2, 3]})
    assert hb.df_read(df) is df


def test_a_missing_path_and_a_bad_type_still_raise(tmp_path):
    with pytest.raises(NameError):
        hb.df_read(str(tmp_path / 'not_here.csv'))
    with pytest.raises(NameError):
        hb.df_read(42)


def test_an_unreadable_file_reports_every_encoding_that_was_tried(tmp_path):
    # The message should say what was attempted, so the reader knows whether to suspect the
    # encoding, the delimiter or the file itself.
    path = tmp_path / 'not_a_csv.csv'
    path.write_bytes(b'\x00\x01\x02\x03\xff\xfe')
    with pytest.raises(NameError) as raised:
        hb.df_read(str(path))
    message = str(raised.value)
    assert 'utf-8-sig' in message and 'latin1' in message
