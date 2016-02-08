#
# Project Ginger S390x
#
# Copyright IBM Corp, 2015-2016
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

import mock
import unittest

import wok.exception as exception
from model.model_utils import get_directories, get_dirname
from model.model_utils import get_row_data, get_rows_info


class GetDirectoriesDirnameUnitTests(unittest.TestCase):
    """
    Unit tests for get_directories() and get_dirname() using mock.patch
    """
    @mock.patch('model.model_utils.glob', autospec=True)
    def test_get_directories(self, mock_glob):
        """
        unittest to validate _list_deviceinfo method
        with empty dict input to it. It should return empty list.
        mock_utils: mock of utils imported in model.storagedevices
        """
        path = "dummypth"
        mock_glob.glob.return_value = "dummyout"
        return_out = get_directories(path)
        mock_glob.glob.assert_called_once_with(path)
        self.assertEqual(return_out, "dummyout")

    def test_get_dirname_integer(self):
        path = 0000
        return_out = get_dirname(path)
        self.assertEqual(return_out, None)

    def test_get_dirname_string(self):
        path = "dummy"
        return_out = get_dirname(path)
        self.assertEqual(return_out, path)

    def test_get_dirname_path_withslash(self):
        path = "dummy/dir"
        return_out = get_dirname(path)
        self.assertEqual(return_out, "dir")

    def test_get_dirname_path_endwithslash(self):
        path = "dummy/dir/"
        return_out = get_dirname(path)
        self.assertEqual(return_out, "dir")

    def test_get_dirname_none_input(self):
        path = None
        return_out = get_dirname(path)
        self.assertEqual(return_out, path)


class GetRowDataUnitTests(unittest.TestCase):
    """
    unit tests for get_row_data() method using mock module
    """
    @mock.patch('model.model_utils.wok_log', autospec=True)
    def test_get_row_data_no_header_match(self, mock_log):
        out = "dummy output"
        header_pattern = r'(\d+)'
        value_pattern = r'(\w+)'
        self.assertRaises(exception.OperationFailed,
                          get_row_data, out, header_pattern,
                          value_pattern)
        mock_log.error.assert_called_with("header is empty for given pattern")

    def test_get_row_data_headerandvalue_match(self):
        out = "dummy output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'\w+\s(\w+)'
        return_out = get_row_data(out, header_pattern, value_pattern)
        self.assertEqual(return_out, {})

    def test_get_row_data_value_none(self):
        out = "dummy output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'\d+\s(\d+)'
        return_out = get_row_data(out, header_pattern, value_pattern)
        self.assertEqual(return_out, {})

    def test_get_row_data_header_value_lenmissmatch(self):
        out = "column1 column2 column3\n0000 output"
        header_pattern = r'(\w+)\s(\w+)\s(\w+)'
        value_pattern = r'(\d+)\s(\w+)'
        return_out = get_row_data(out, header_pattern, value_pattern)
        self.assertEqual(return_out, {})

    def test_get_row_data_valid(self):
        out = "column column2\ndummy output"
        header_pattern = r'(column)\s(column2)'
        value_pattern = r'(dummy)\s(\w+)'
        return_out = get_row_data(out, header_pattern, value_pattern)
        self.assertEqual(return_out, {"column": "dummy", "column2": "output"})


class GetRowsInfoUnitTests(unittest.TestCase):
    """
    unit tests for get_rows_info() method using mock module
    """
    @mock.patch('model.model_utils.wok_log', autospec=True)
    def test_get_rows_info_no_header_match(self, mock_log):
        """
        unit test to validate get_rows_info() method with no
        match for header regex
        mock_log: mock of wok_log of model.utils
        get_rows_info() should raise exception
        """
        out = "dummy output\n0000 output"
        header_pattern = ""
        value_pattern = r'\d+\s(\w+)'
        self.assertRaises(exception.OperationFailed,
                          get_rows_info, out, header_pattern,
                          value_pattern)
        mock_log.error.assert_called_with("header is empty for given pattern")

    def test_nokey_novalue_match(self):
        """
        unit test to validate get_rows_info() by passing key as none
        and header matches but values are not matched
        get_rows_info() should return empty list
        """
        out = "dummy output\n0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'\d+\s\d(\w+)'  # regex doesn't match values in out
        return_value = get_rows_info(out, header_pattern, value_pattern)
        self.assertEqual(return_value, [])

    def test_withkey_novalue_match(self):
        """
        unit test to validate get_rows_info() by passing key as none
        and header matches but values are not matched
        get_rows_info() should return empty dictionary
        """
        out = "dummy output\n0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'\d+\s\d(\w+)'  # regex doesn't match values in out
        return_value = get_rows_info(out, header_pattern,
                                     value_pattern, unique_col='dummy')
        self.assertEqual(return_value, {})

    def test__header_value_lenmissmatch(self):
        """
        unit test to validate get_rows_info() with miss match in
        length of header items parsed out using header regex and that
        of value items parsed out using value regex.
        get_rows_info() should return {} with key
        """
        out = "dummy output\n \n 0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'\d+\s(\w+)'

        def format_data(data):
            return {"key": "value", "dummy": "output"}
        unique_col = "key"
        devices = get_rows_info(out, header_pattern,
                                value_pattern, unique_col=unique_col,
                                format_data=format_data)
        self.assertEqual(devices, {})

    def test_success_invalidkey(self):
        """
        unit test to validate get_rows_info() by passing invalid unique_col
        get_rows_info() should should raise KeyError exception
        """
        out = "dummy output\n0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'(\d+)\s(\w+)'

        def format_data(dict_in):
            return {"key": "value", "dummy": "output"}
        unique_col = "invalid_key"
        self.assertRaises(KeyError, get_rows_info, out, header_pattern,
                          value_pattern, unique_col=unique_col,
                          format_data=format_data, hdr_index=0,
                          val_start_index=1)

    def test_success_withkey(self):
        """
        unit test to validate get_rows_info() success scenario
        (with unique_col value passed) in which header and values
        were retrieved successfully formatted it with format_data.
        get_rows_info() should return formatted output as dictionary
        """
        out = "dummy output\n0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'(\d+)\s(\w+)'

        def format_data(dict_in):
            return {"key": "value", "dummy": "output"}
        unique_col = "key"
        devices = get_rows_info(out, header_pattern, value_pattern,
                                unique_col=unique_col,
                                format_data=format_data,
                                hdr_index=0, val_start_index=1)
        self.assertEqual(devices,
                         {"value": {"key": "value",
                          "dummy": "output"}})

    def test_success_without_key(self):
        """
        unit test to validate get_rows_info() success scenario
        (without passing unique_col value) in which header and
        values were retrieved successfully formatted it with format_data.
        get_rows_info() should return formatted output as list
        """
        out = "dummy output\n0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'(\d+)\s(\w+)'

        def format_data(dict_in):
            return {"key": "value", "dummy": "output"}
        devices = get_rows_info(out, header_pattern, value_pattern,
                                format_data=format_data,
                                hdr_index=0, val_start_index=1)
        self.assertEqual(devices, [{"key": "value",
                                   "dummy": "output"}])

    def test_success_without_format_data(self):
        """
        unit test to validate get_rows_info() method success scenario
        without passing format_data.
        get_rows_info() should return the header and values mapped
        """
        out = "dummy output\n0000 output"
        header_pattern = r'(\w+)\s(\w+)'
        value_pattern = r'(\d+)\s(\w+)'
        unique_col = 'dummy'

        devices = get_rows_info(out, header_pattern, value_pattern,
                                unique_col=unique_col,
                                hdr_index=0, val_start_index=1)
        self.assertEqual(devices, {'0000': {"dummy": "0000",
                                   "output": "output"}})
