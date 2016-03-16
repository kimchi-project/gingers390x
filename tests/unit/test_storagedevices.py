# -*- coding: utf-8 -*-
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
from model.storagedevices import _bring_offline, _bring_online
from model.storagedevices import _byte_to_binary, _device_offline
from model.storagedevices import _device_online, _format_lscss
from model.storagedevices import _get_dasdeckd_devices, _get_deviceinfo
from model.storagedevices import _get_paths, _get_zfcp_devices
from model.storagedevices import _hex_to_binary, _is_dasdeckd_device
from model.storagedevices import _is_dasdeckd_persisted, _is_online
from model.storagedevices import _is_zfcp_device, _list_devicesinfo
from model.storagedevices import _persist_dasdeckd_device
from model.storagedevices import _persist_zfcp_device
from model.storagedevices import StorageDeviceModel, StorageDevicesModel
from model.storagedevices import _unpersist_dasdeckd_device
from model.storagedevices import _unpersist_zfcp_device, _validate_device


syspath_eckd = "/sys/bus/ccw/drivers/dasd-eckd/0.*/"
syspath_zfcp = "/sys/bus/ccw/drivers/zfcp/0.*/"
DASD_CONF = '/etc/dasd.conf'
ZFCP_CONF = '/etc/zfcp.conf'


class ListDevicesInfoUnitTests(unittest.TestCase):
    """
    Unit tests for _list_devicesinfo() method
    """

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_list_devicesinfo_empty_dict(self, mock_utils):
        """
        unittest to validate _list_deviceinfo method
        with empty dict input to it. It should return empty list.
        mock_utils: mock of utils imported in model.storagedevices
        """
        empty = {}
        dummy_paths = ['/sys']
        devices_info = _list_devicesinfo(empty, dummy_paths)
        self.assertEqual(devices_info, [])
        self.assertFalse(mock_utils.get_dirname.called,
                         msg='Unexpected call to mock_utils.get_dirname()')

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_list_devicesinfo_empty_paths(self, mock_utils):
        """
        unittest to validate _list_deviceinfo method
        with empty paths input to it. It should return empty list.
        mock_utils: mock of utils imported in model.storagedevices
        """
        dummy_devices = {"0.0.2020": {"name": "0.0.2020"}}
        empty_paths = []
        devices_info = _list_devicesinfo(dummy_devices, empty_paths)
        self.assertEqual(devices_info, [])
        self.assertFalse(mock_utils.get_dirname.called,
                         msg='Unexpected call to mock_utils.get_dirname()')

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_list_devicesinfo_nomatch(self, mock_utils):
        """
        unittest to validate _list_deviceinfo method
        where dict input does not have matching devices present in paths input.
        It should return empty list.
        mock_utils: mock of utils imported in model.storagedevices
        """
        dummy_devices = {"0.0.2020": {"name": "0.0.2020"}}
        dummy_paths = ['/sys/bus/ccw/drivers/dasd-eckd/0.1.1000/']
        mock_utils.get_dirname.return_value = "0.1.1000"
        devices_info = _list_devicesinfo(dummy_devices, dummy_paths)
        self.assertEqual(devices_info, [])
        mock_utils.get_dirname.assert_called_with(dummy_paths[0])

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_list_devicesinfo_somematch(self, mock_utils):
        """
        unittest to validate _list_deviceinfo method
        where dict input has matching devices present in paths input.
        It should return list of device info.
        mock_utils: mock of utils imported in model.storagedevices
        """
        dummy_devices = {"0.0.2020": {"name": "0.0.2020"},
                         "0.0.2021": {"name": "0.0.2021"},
                         "0.1.2020": {"name": "0.1.2020"}}
        dummy_paths = ['/sys/bus/ccw/drivers/dasd-eckd/0.1.1000/',
                       '/sys/bus/ccw/drivers/dasd-eckd/0.1.2020/',
                       '/sys/bus/ccw/drivers/dasd-eckd/0.0.2020/']
        mock_utils.get_dirname.side_effect = ["0.1.1000",
                                              "0.1.2020",
                                              "0.0.2020"]
        devices_info = _list_devicesinfo(dummy_devices, dummy_paths)
        self.assertEqual(devices_info,
                         [{"name": "0.1.2020"},
                          {"name": "0.0.2020"}])


class FormatLscssUnitTests(unittest.TestCase):
    """
    unit tests for _format_lscss() method
    """

    def test_format_lscss_Noneinput(self):
        """
        unit test to validate _format_lscss() with None input
        _format_lscss() should return None
        """
        device = None
        formated_devices = _format_lscss(device)
        self.assertEqual(formated_devices, None)

    def test_format_lscss_emptyjsoninput(self):
        """
        unit test to validate _format_lscss() with empty json i/p
        _format_lscss() should return empty json
        """
        device = {}
        formated_devices = _format_lscss(device)
        self.assertEqual(formated_devices, device)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_format_lscss_keyerror(self, mock_log):
        """
        unit test to validate _format_lscss() with wrong keys
        _format_lscss() should raise KeyError
        """
        device = {"Device": "0.0.0200", "Subchan": "0.0.0000",
                  "DevType": "3390/0a", "CU Type": "3390/0a",
                  "Use": "", "PIM": "e0", "PAM": "e0",
                  "POM": "ff", "Invalid Key": "0000"}
        log_msg = 'Issue while formating lscss dictionary output'
        self.assertRaises(KeyError, _format_lscss, device)
        mock_log.error.assert_called_with(log_msg)

    def test_format_lscss_use_yes(self):
        """
        unit test to validate _format_lscss() with "Use" as "yes"
        """
        device = {"Device": "0.0.0200", "Subchan": "0.0.0000",
                  "DevType": "3390/0a", "CU Type": "3390/0a",
                  "Use": "yes", "PIM": "e0", "PAM": "e0",
                  "POM": "ff", "CHPIDs": "b0b10d00 00000000"}
        output = {"device": "0.0.0200", "sub_channel": "0.0.0000",
                  "device_type": "3390/0a", "cu_type": "3390/0a",
                  "status": "online", "enabled_chipids":
                  ["b0", "b1", "0d"], "installed_chipids":
                  ["b0", "b1", "0d"]}
        formated_devices = _format_lscss(device)
        self.assertEqual(formated_devices, output)

    def test_format_lscss_use_blank(self):
        """
        unit test to validate _format_lscss() with "Use" as "blank"
        and pim mask equal to pam mask
        """
        device = {"Device": "0.0.0200", "Subchan": "0.0.0000",
                  "DevType": "3390/0a", "CU Type": "3390/0a",
                  "Use": "  ", "PIM": "e0", "PAM": "e0",
                  "POM": "ff", "CHPIDs": "b0b10d00 00000000"}
        output = {"device": "0.0.0200", "sub_channel": "0.0.0000",
                  "device_type": "3390/0a", "cu_type": "3390/0a",
                  "status": "offline", "enabled_chipids":
                  ["b0", "b1", "0d"], "installed_chipids":
                  ["b0", "b1", "0d"]}
        formated_devices = _format_lscss(device)
        self.assertEqual(formated_devices, output)

    def test_format_lscss_use_pim_notequal_pam(self):
        """
        unit test to validate _format_lscss() with pim mask
        not equal to pam mask
        """
        device = {"Device": "0.0.0200", "Subchan": "0.0.0000",
                  "DevType": "3390/0a", "CU Type": "3390/0a",
                  "Use": "  ", "PIM": "80", "PAM": "e0",
                  "POM": "ff", "CHPIDs": "b0b10d00 00000000"}
        output = {"device": "0.0.0200", "sub_channel": "0.0.0000",
                  "device_type": "3390/0a", "cu_type": "3390/0a",
                  "status": "offline", "enabled_chipids":
                  ["b0", "b1", "0d"], "installed_chipids":
                  ["b0"]}
        formated_devices = _format_lscss(device)
        self.assertEqual(formated_devices, output)


class GetPathsUnitTests(unittest.TestCase):
    """
    unit tests for _get_paths() method
    """

    def test_get_paths_success(self):
        """
        unit test to test for a valid scenario valid chipids
        and binary value of pam to get the installed paths
        """
        chipid = 'fa000000 00000000'
        bin_pam = '10000000'
        installed_paths = ['fa']
        out = _get_paths(bin_pam, chipid)
        self.assertEqual(installed_paths, out)

    def test_get_paths_invalid_binaryval(self):
        """
        unit test to test for a invalid scenario for valid chipids
        and invalid binary value of pam to get the installed paths
        """
        chipid = 'fa000000 00000000'
        bin_pam = '11000000'
        out = _get_paths(bin_pam, chipid)
        installed_paths = ['fa']
        self.assertNotEqual(installed_paths, out)

    def test_get_paths_invalid_chipid(self):
        """
        unit test to test for a valid scenario for invalid chipids
        and valid binary value of pam to get the installed paths
        """
        chipid = 'ds0000 00000000'
        bin_pam = '10000000'
        out = _get_paths(bin_pam, chipid)
        installed_paths = ['fa']
        self.assertNotEqual(installed_paths, out)

    def test_byte_to_binary_success(self):
        """
        unit test to test the conversion of byte in binary value to get the
        valid binary value for the corresponding byte
        """
        val = '\x80'
        binaryval = '10000000'
        out = _byte_to_binary(ord(val))
        self.assertEqual(binaryval, out)

    def test_byte_to_binary_failure(self):
        """
        unit test to test the conversion of byte in binary value to get the
        invalid binary value for the corresponding byte
        """
        val = '\x80'
        binaryval = '1230000'
        out = _byte_to_binary(ord(val))
        self.assertNotEqual(binaryval, out)

    def test_hex_to_binary_success(self):
        """
        unit test to test the conversion of a hexadecimal value to binary
        for a valid hexadecimal value to fetch the the corresponding binary
        value
        """
        val = '80'
        binaryval = '10000000'
        out = _hex_to_binary(val)
        self.assertEqual(binaryval, out)

    def test_hex_to_binary_failure(self):
        """
        unit test to test the conversion of a hexadecimal value to binary
        for a valid hexadecimal value to fetch the the corresponding
        invalid binary value
        """
        val = 'e0'
        binaryval = '10000000'
        out = _hex_to_binary(val)
        self.assertNotEqual(binaryval, out)


class GetDeviceInfoUnitTests(unittest.TestCase):
    """
    unit tests for _get_deviceinfo() method
    """
    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices._format_lscss', autospec=True)
    def test_get_deviceinfo_somedevice(self, mock_format_lscss, mock_utils):
        """
        unit test to validate _get_deviceinfo() method with
        matching device
        _get_deviceinfo() should return _format_lscss() o/p
        """
        device = "xxx"
        header_pattern = "(Device)\s+(Subchan)\.\s+(DevType)\s+(CU\ Type)\s+" \
                         "(Use)\s+(PIM)\s+(PAM)\s+(POM)\s+(CHPIDs)$"
        device_pattern = "(xxx)\s+(\d\.\d\.[0-9a-fA-F]{4})\s+(\w+\/\w+)" \
                         "\s+(\w+\/\w+)\s(\s{3}|yes)\s+([0-9a-fA-F]{2})\s+" \
                         "([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})\s+(\w+\s\w+)"
        mock_utils.get_row_data.return_value = {}
        mock_format_lscss.return_value = {}
        deviceinfo = _get_deviceinfo('', device)
        mock_utils.get_row_data.assert_called_with('', header_pattern,
                                                   device_pattern)
        mock_format_lscss.assert_called_with(mock_utils.get_row_data.
                                             return_value)
        self.assertEqual(deviceinfo, {})

    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices._format_lscss', autospec=True)
    def test_get_deviceinfo_emptydevice(self, mock_format_lscss, mock_utils):
        """
        unit test to validate _get_deviceinfo() with empty device i/p
        _get_deviceinfo() should return device
        """
        device = ""
        deviceinfo = _get_deviceinfo('', device)
        self.assertFalse(mock_utils.get_row_data.called,
                         msg='Unexpected call to mock_utils.get_row_data()')
        self.assertFalse(mock_format_lscss.called,
                         msg='Unexpected call to mock_format_lscss()')
        self.assertEqual(deviceinfo, device)

    @mock.patch('model.storagedevices._format_lscss', autospec=True)
    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_deviceinfo_keyerror(self, mock_utils,
                                     mock_log, mock_format_lscss):
        """
        unit test to validate _get_deviceinfo() with key error raised
        by format lscss
        """
        mock_utils.get_row_data.return_value = {"key": "value"}
        mock_format_lscss.side_effect = KeyError
        self.assertRaises(KeyError, _get_deviceinfo, '', 'gdhdh')
        mock_log.error.assert_called_with('lscss column key not found')


class GetListUnitTests(unittest.TestCase):
    """
    unit tests for get_list() of StorageDevicesModel()
    """
    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    @mock.patch('model.storagedevices._format_lscss', autospec=True)
    @mock.patch('model.storagedevices._list_devicesinfo', autospec=True)
    def test_get_list_type_none(self, mock_list_deviceinfo,
                                mock_format_lscss,
                                mock_run_command, mock_utils):
        """
        unit test to validate get_list() of StorageDevicesModel()
        with flag filter None
        """
        storagedevicesmodel = StorageDevicesModel()
        command = ["lscss"]
        header_pattern = "(Device)\s+(Subchan)\." \
                         "\s+(DevType)\s+(CU\ Type)\s+" \
                         "(Use)\s+(PIM)\s+(PAM)" \
                         "\s+(POM)\s+(CHPIDs)$"
        device_pattern = "(\d\.\d\.[0-9a-fA-F]{4})" \
                         "\s+(\d\.\d\.[0-9a-fA-F]{4})\s+" \
                         "(\w+\/\w+)\s+(\w+\/\w+)" \
                         "\s(\s{3}|yes)\s+([0-9a-fA-F]{2})\s+" \
                         "([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})" \
                         "\s+(\w+\s\w+)"
        mock_utils.get_directories.return_value = ["abc"]
        mock_utils.get_rows_info.return_value = {}
        mock_run_command.return_value = ["", "", 0]
        storagedevicesmodel.get_list()
        calls = [('/sys/bus/ccw/drivers/dasd-eckd/0.*/',),
                 ('/sys/bus/ccw/drivers/zfcp/0.*/',)]
        for i in range(0, 1):
            x, y = mock_utils.get_directories.call_args_list[i]
            assert x == calls[i]
        assert mock_utils.get_directories.call_count == 2
        mock_run_command.assert_called_with(command)
        mock_utils.get_rows_info.assert_called_once_with(
            "",
            header_pattern,
            device_pattern,
            unique_col='device',
            format_data=mock_format_lscss)
        mock_list_deviceinfo.assert_called_once_with({}, ["abc", "abc"])

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_list_no_device(self, mock_utils):
        """
        unit test to validate get_list() of StorageDevicesModel()
        when device found
        """
        storagedevicesmodel = StorageDevicesModel()
        mock_utils.get_directories.return_value = []
        returns = storagedevicesmodel.get_list()
        calls = [('/sys/bus/ccw/drivers/dasd-eckd/0.*/',),
                 ('/sys/bus/ccw/drivers/zfcp/0.*/',)]
        for i in range(0, 2):
            x, y = mock_utils.get_directories.call_args_list[i]
            assert x == calls[i]
        assert returns == []

    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    @mock.patch('model.storagedevices._format_lscss', autospec=True)
    @mock.patch('model.storagedevices._list_devicesinfo', autospec=True)
    def test_get_list_type_dasd(self, mock_list_deviceinfo,
                                mock_format_lscss,
                                mock_run_command, mock_utils):
        """
        unit test to validate get_list() of StorageDevicesModel()
        with flag filter dasd-eckd
        """
        storagedevicesmodel = StorageDevicesModel()
        command = ["lscss"]
        header_pattern = "(Device)\s+(Subchan)\." \
                         "\s+(DevType)\s+(CU\ Type)\s+" \
                         "(Use)\s+(PIM)\s+(PAM)" \
                         "\s+(POM)\s+(CHPIDs)$"
        device_pattern = "(\d\.\d\.[0-9a-fA-F]{4})" \
                         "\s+(\d\.\d\.[0-9a-fA-F]{4})\s+" \
                         "(\w+\/\w+)\s+(\w+\/\w+)" \
                         "\s(\s{3}|yes)\s+([0-9a-fA-F]{2})\s+" \
                         "([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})" \
                         "\s+(\w+\s\w+)"
        mock_utils.get_directories.return_value = ["abc"]
        mock_utils.get_rows_info.return_value = {}
        mock_run_command.return_value = ["", "", 0]
        storagedevicesmodel.get_list("dasd-eckd")
        calls = '/sys/bus/ccw/drivers/dasd-eckd/0.*/'
        mock_utils.get_directories.assert_called_once_with(calls)
        mock_run_command.assert_called_with(command)
        mock_utils.get_rows_info.assert_called_once_with(
            "",
            header_pattern,
            device_pattern,
            unique_col='device',
            format_data=mock_format_lscss)
        mock_list_deviceinfo.assert_called_once_with({}, ["abc"])

    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    @mock.patch('model.storagedevices._format_lscss', autospec=True)
    @mock.patch('model.storagedevices._list_devicesinfo', autospec=True)
    def test_get_list_type_zfcp(self, mock_list_deviceinfo,
                                mock_format_lscss,
                                mock_run_command, mock_utils):
        """
        unit test to validate get_list() of StorageDevicesModel()
        with flag filter as zfcp
        """
        storagedevicesmodel = StorageDevicesModel()
        command = ["lscss"]
        header_pattern = "(Device)\s+(Subchan)\." \
                         "\s+(DevType)\s+(CU\ Type)\s+" \
                         "(Use)\s+(PIM)\s+(PAM)\s+(POM)" \
                         "\s+(CHPIDs)$"
        device_pattern = r'(\d\.\d\.[0-9a-fA-F]{4})\s+' \
                         r'(\d\.\d\.[0-9a-fA-F]{4})\s+' \
                         r'(\w+\/\w+)\s+' \
                         r'(\w+\/\w+)\s' \
                         r'(\s{3}|yes)\s+' \
                         r'([0-9a-fA-F]{2})\s+' \
                         r'([0-9a-fA-F]{2})\s+' \
                         r'([0-9a-fA-F]{2})\s+' \
                         r'(\w+\s\w+)'
        mock_utils.get_directories.return_value = ["abc"]
        mock_run_command.return_value = ["", "", 0]
        mock_utils.get_rows_info.return_value = {}
        storagedevicesmodel.get_list("zfcp")
        calls = '/sys/bus/ccw/drivers/zfcp/0.*/'
        mock_utils.get_directories.assert_called_once_with(calls)
        mock_run_command.assert_called_with(command)
        mock_utils.get_rows_info.assert_called_once_with(
            "",
            header_pattern,
            device_pattern,
            unique_col='device',
            format_data=mock_format_lscss)
        mock_list_deviceinfo.assert_called_once_with({}, ["abc"])

    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_get_list_type_wrong(self, mock_log, mock_run_command, mock_utils):
        """
        unit test to validate get_list() of StorageDevicesModel()
        with invalid flag filter
        """
        storagedevicesmodel = StorageDevicesModel()
        mock_run_command.return_value = ["", "", 0]
        self.assertRaises(exception.InvalidParameter,
                          storagedevicesmodel.get_list, 'abcé')
        mock_utils.get_directories(
            "/sys/bus/ccw/drivers/dasd-eckd/0.*/").assert_not_called()
        mock_utils.get_directories(
            "/sys/bus/ccw/drivers/zfcp/0.*/").assert_not_called()
        mock_log.error.assert_called_with("Invalid _type given. _type: abcé")

    @mock.patch('model.storagedevices.utils', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_get_list_rc_1(self, mock_log, mock_run_command, mock_utils):
        """
        unit test to validate get_list() of StorageDevicesModel()
        when run_command has non zero return code
        """
        storagedevicesmodel = StorageDevicesModel()
        mock_utils.get_directories.return_value = ["abc"]
        mock_run_command.return_value = ["dummy_out", "dummy_err", 1]
        self.assertRaises(exception.OperationFailed,
                          storagedevicesmodel.get_list)
        mock_log.error.assert_called_with("dummy_err")


class GetStoragedeviceUnitTests(unittest.TestCase):
    """
    unit tests for get_storagedevice() and lookup() of StorageDeviceModel()
    """
    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices._is_zfcp_device', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    @mock.patch('model.storagedevices._get_deviceinfo', autospec=True)
    def test_get_storagedevice(self, mock_get_deviceinfo,
                               mock_run_command, mock_is_zfcp_device,
                               mock_is_dasdeckd_device,
                               mock_validate_device):
        """
        unittest to validate get_storagedevice() method,
        success scenario (ie., i/p device is either dasd-eckd
        or zfcp device and lscss loads device info)
        mock_get_deviceinfo: mock of _get_deviceinfo()
        method of model.storagedevices
        mock_run_command: mock of wok.utils.run_command imported
                        in model.storagedevices
        mock_is_zfcp_device: mock of _is_zfcp_device() method of
                              model.storagedevices
        mock_is_dasdeckd_device: mock of _is_dasdeckd_device() of
                                 model.storagedevices
        mock_validate_device: mock of _validate_device() of
                                  model.storagedevices
        on success, get_storagedevice() method should return
                    formatted output of lscss command
        """
        command = ['lscss', '-d', 'dummydevice']
        mock_run_command.return_value = ["dummyout\n\ndummydevice", "", 0]
        mock_is_dasdeckd_device.return_value = True
        mock_is_zfcp_device.return_value = False
        mock_validate_device.return_value = "dummydevice"
        mock_get_deviceinfo.return_value = {'dummydevice': 'dummyout'}
        storagedevicemodel = StorageDeviceModel()
        return_value = storagedevicemodel.get_storagedevice('dummydevice')
        mock_run_command.assert_called_once_with(command)
        mock_get_deviceinfo.assert_called_once_with('dummyout\n\ndummydevice',
                                                    "dummydevice")
        mock_is_dasdeckd_device.assert_called_once_with('dummydevice')
        self.assertFalse(mock_is_zfcp_device.called,
                         msg='Unexpected call to mock_is_zfcp_device()')
        self.assertEqual(return_value, {'dummydevice': 'dummyout'})

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices._is_zfcp_device', autospec=True)
    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    def test_get_storagedevice_blank_out(self, mock_run_command, mock_log,
                                         mock_is_zfcp_device,
                                         mock_is_dasdeckd_device,
                                         mock_validate_device):
        """
        unittest to validate get_storagedevice() method, with lscss
        command returning empyt output
        mock_log: mock of wok_log() of model.storagedevices
        mock_run_command: mock of wok.utils.run_command imported
                        in model.storagedevices
        mock_is_zfcp_device: mock of _is_zfcp_device() method of
                              model.storagedevices
        mock_is_dasdeckd_device: mock of _is_dasdeckd_device() of
                                 model.storagedevices
        mock_validate_device: mock of _validate_device() of
                                  model.storagedevices
        expected behavior : get_storagedevice() method should raise
                    OperationFailed exception
        """
        command = ["lscss", '-d', "dummydevice"]
        mock_run_command.return_value = ["", "", 0]
        mock_is_dasdeckd_device.return_value = True
        mock_is_zfcp_device.return_value = False
        mock_validate_device.return_value = "dummydevice"
        storagedevicemodel = StorageDeviceModel()
        self.assertRaises(exception.OperationFailed,
                          storagedevicemodel.get_storagedevice,
                          'dummydevice')
        mock_run_command.assert_called_once_with(command)
        mock_is_dasdeckd_device.assert_called_once_with('dummydevice')
        self.assertFalse(mock_is_zfcp_device.called,
                         msg='Unexpected call to mock_is_zfcp_device()')
        mock_log.error.assert_called_with("lscss output is either "
                                          "blank or None")

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    def test_get_storagedevice_invalid_input(self, mock_validate_device):
        """
        unittest to validate get_storagedevice() method, with
        invalid input(invalid deviec id)
        mock_validate_device: mock of _validate_device() of
                                  model.storagedevices
        expected behavior : get_storagedevice() method should raise
                    InvalidParameter exception
        """
        mock_validate_device.side_effect = exception.InvalidParameter
        storagedevicemodel = StorageDeviceModel()
        self.assertRaises(exception.InvalidParameter,
                          storagedevicemodel.get_storagedevice, 'xyz')

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices._is_zfcp_device', autospec=True)
    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_get_storagedevice_otherdevice(self, mock_log,
                                           mock_is_zfcp_device,
                                           mock_is_dasdeckd_device,
                                           mock_validate_device):
        """
        unittest to validate get_storagedevice() method, with device
        which is not of type dasd-eckd or  zfcp
        mock_log: mock of wok_log() of model.storagedevices
        mock_is_zfcp_device: mock of _is_zfcp_device() method of
                              model.storagedevices
        mock_is_dasdeckd_device: mock of _is_dasdeckd_device() of
                                 model.storagedevices
        mock_validate_device: mock of _validate_device() of
                                  model.storagedevices
        expected behavior : get_storagedevice() method should raise
                    InvalidParameter exception
        """
        device = 'dummy_device'
        mock_is_dasdeckd_device.return_value = False
        mock_is_zfcp_device.return_value = False
        mock_validate_device.return_value = device
        storagedevicemodel = StorageDeviceModel()
        self.assertRaises(exception.InvalidParameter,
                          storagedevicemodel.get_storagedevice,
                          device)
        mock_is_dasdeckd_device.assert_called_once_with(device)
        mock_is_zfcp_device.assert_called_once_with(device)
        mock_log.error.assert_called_with("Given device "
                                          "id is of type dasd-eckd or"
                                          " zfcp. Device: %s" % device)

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices._is_zfcp_device', autospec=True)
    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    def test_get_storagedevice_rc_1(self, mock_run_command, mock_log,
                                    mock_is_zfcp_device,
                                    mock_is_dasdeckd_device,
                                    mock_validate_device):
        """
        unittest to validate get_storagedevice() method, with lscss
        command returning non zero return code
        mock_log: mock of wok_log() of model.storagedevices
        mock_run_command: mock of wok.utils.run_command imported
                        in model.storagedevices
        mock_is_zfcp_device: mock of _is_zfcp_device() method of
                              model.storagedevices
        mock_is_dasdeckd_device: mock of _is_dasdeckd_device() of
                                 model.storagedevices
        mock_validate_device: mock of _validate_device() of
                                  model.storagedevices
        expected behavior : get_storagedevice() method should raise
                    OperationFailed exception
        """
        command = ["lscss", '-d', "dummydasddevice"]
        mock_run_command.return_value = ["", "dummyerr", 1]
        mock_validate_device.return_value = "dummydasddevice"
        mock_is_dasdeckd_device.return_value = True
        mock_is_zfcp_device.return_value = False
        storagedevicemodel = StorageDeviceModel()
        self.assertRaises(exception.OperationFailed,
                          storagedevicemodel.get_storagedevice,
                          'dummydasddevice')
        mock_run_command.assert_called_once_with(command)
        mock_is_dasdeckd_device.assert_called_once_with('dummydasddevice')
        self.assertFalse(mock_is_zfcp_device.called,
                         msg='Unexpected call to mock_is_zfcp_device()')
        mock_log.error.assert_called_with("dummyerr")

    @mock.patch('model.storagedevices.StorageDeviceModel.get_storagedevice')
    def test_lookup(self, mock_get_storagedevice):
        """
        unittest to validate lookup() method
        mock_get_storagedevice: mock of get_storagedevice() method
                            of StorageDeviceModel() in model.storagedevices
        """
        # Fix me: resolve issue after including autospec=True in mock.patch
        storagedevicemodel = StorageDeviceModel()
        storagedevicemodel.lookup('dummy')
        mock_get_storagedevice.assert_called_with("dummy")


class StorageDevicePostOperationUnitTests(unittest.TestCase):
    """
    Unit tests for post operation on single
    resource - online() and  offline() using mock.patch
    """
    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._device_online', autospec=True)
    def test_online_valid_device(self, mock_device_online,
                                 mock_validate_device):
        """
        unit test to validate online operation with valid device id
        (_validate_device and _device_online goes fine)
        mock_validate_device: mock of _validate_device model.storagedevices
        mock_device_online: mock of _device_online model.storagedevices
        """
        device = 'dummy_device'
        mock_validate_device.return_value = 'dummy_device'
        storage_device_model = StorageDeviceModel()
        storage_device_model.online(device)
        mock_validate_device.assert_called_once_with(device)
        mock_device_online.assert_called_once_with(device)

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._device_online', autospec=True)
    def test_online_invalid_device(self, mock_device_online,
                                   mock_validate_device):
        """
        unit test to validate online operation with invalid device id
        (_validate_device raises an exception for invalid device id)
        mock_validate_device: mock of _validate_device model.storagedevices
        mock_device_online: mock of _device_online model.storagedevices
        """
        device = 'dummy_device'
        mock_validate_device.side_effect = exception.OperationFailed
        storage_device_model = StorageDeviceModel()
        self.assertRaises(exception.OperationFailed,
                          storage_device_model.online, device)
        mock_validate_device.assert_called_once_with(device)
        self.assertFalse(mock_device_online.called,
                         msg='Unexpected call to mock_device_online()')

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._device_offline', autospec=True)
    def test_offline_valid_device(self, mock_device_offline,
                                  mock_validate_device):
        """
        unit test to validate offline operation with valid device id
        (_validate_device and _device_offline goes fine)
        mock_validate_device: mock of _validate_device model.storagedevices
        mock_device_offline: mock of _device_offline model.storagedevices
        """
        device = 'dummy_device'
        mock_validate_device.return_value = 'dummy_device'
        storage_device_model = StorageDeviceModel()
        storage_device_model.offline(device)
        mock_validate_device.assert_called_once_with(device)
        mock_device_offline.assert_called_once_with(device)

    @mock.patch('model.storagedevices._validate_device', autospec=True)
    @mock.patch('model.storagedevices._device_offline', autospec=True)
    def test_offline_invalid_device(self, mock_device_offline,
                                    mock_validate_device):
        """
        unit test to validate offline operation with invalid device id
        (_validate_device raises OperationFailed exception)
        mock_validate_device: mock of _validate_device model.storagedevices
        mock_device_offline: mock of _device_offline model.storagedevices
        """
        device = 'dummy_device'
        mock_validate_device.side_effect = exception.OperationFailed
        storage_device_model = StorageDeviceModel()
        self.assertRaises(exception.OperationFailed,
                          storage_device_model.offline, device)
        mock_validate_device.assert_called_once_with(device)
        self.assertFalse(mock_device_offline.called,
                         msg='Unexpected call to mock_device_offline()')


class ValidateDeviceUnitTests(unittest.TestCase):
    """
    Unit tests for _validate_device() method
    """

    def test_validate_device_withdot(self):
        """
        unit test to validate valid device id having dot in it
        _validate_device() method should return the same device id
        """
        device = "0.0.9845"
        out = _validate_device(device)
        self.assertEqual(out, device)

    def test_valiadte_device_withoutdot(self):
        """
        unit test to validate valid device id which doesn't have dot in it
        _validate_device() method should return same device id with "0.0."
        prepended to it
        """
        device = "9845"
        out = _validate_device(device)
        self.assertEqual(out, "0.0." + device)

    def _test_validate_device_validdev_unicode(self):
        """
        unit test to validate valid device id of type unicode
        reason for unicode type:
                    from api, device id is passed as unicode
        _validate_device() method should return
                                the same device id but type string
        """
        device = u'0.1.aFa0'
        out = _validate_device(device)
        self.assertEqual(out, str(device))

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_validate_device_invaliddev(self, mock_log):
        """
        unit test to validate invalide device id
        :param mock_log: mock of wok_log imported
        in model.storagedevices
        method should raise InvalidParameter exception and
        error message should be logged in wok_log.error
        """
        device = 'xFxc'
        self.assertRaises(exception.InvalidParameter, _validate_device, device)
        mock_log.error.assert_called_with("Invalid device id. Device: "
                                          "0.0." + device)

    def test_validate_device_integer(self):
        """
        unit test to validate valid device id of int type
        mock_log: mock of wok_log imported in model.storagedevices
        method should raise InvalidParameter exception and
        error message should be logged in wok_log.error
        """
        device = 9999
        out = _validate_device(device)
        self.assertEqual(out, "0.0." + str(device))

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_validate_device_emptydev(self, mock_log):
        """
        unit test to validate empty device id
        mock_log: mock of wok_log imported in model.storagedevices
        method should raise InvalidParameter exception and
        error message should be logged in wok_log.error
        """
        device = " "
        self.assertRaises(exception.InvalidParameter, _validate_device, device)
        mock_log.error.assert_called_with("Device id is empty. Device: %s"
                                          % device)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    def test_validate_device_emptyunicode(self, mock_log):
        """
        unit test to validate empty device id of type unicode
        reason for unicode type: from api, device id is passed as unicode
        mock_log: mock of wok_log imported in model.storagedevices
        method should raise InvalidParameter exception and
        error message should be logged in wok_log.error
        """
        device = u" "
        self.assertRaises(exception.InvalidParameter, _validate_device,
                          device)
        mock_log.error.assert_called_with("Device id is empty. Device: %s"
                                          % device)


class DeviceOnlineUnitTests(unittest.TestCase):
    """
    Unit tests for _device_online() method
    """
    @mock.patch('model.storagedevices._persist_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_persisted', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices.RollbackContext', autospec=True)
    @mock.patch('model.storagedevices._is_online', autospec=True)
    @mock.patch('model.storagedevices._bring_online', autospec=True)
    def test_device_online_success(self, mock_bring_online, mock_is_online,
                                   mock_rollback, mock_is_dasdeckd_device,
                                   mock_is_dasdeckd_persisted,
                                   mock_persist_dasdeckd_device):
        """
        unit test to validate device_online with success scenario
        mock_bring_online: mock of _bring_online() of model.storagedevices
        mock_is_online: mock of _is_online() of model.storagedevices
        mock_rollback: mock of wok.rollbackcontext imported as
                        RollbackContext in model.storagedevices
        mock_is_dasdeckd_device : mock of
        _is_dasdeckd_device() of model.storagedevices
        mock_is_dasdeckd_persisted : mock of
        _is_dasdeckd_persisted() of model.storagedevices
        mock_persist_dasdeckd_device : mock of
        _persist_dasdeckd_device() of model.storagedevices
        on success device_online() method doesn't return anything
        """
        device = 'dummy_device'
        mock_is_online.return_value = False
        mock_is_dasdeckd_device.return_value = True
        mock_is_dasdeckd_persisted.return_value = False
        _device_online(device)
        mock_is_online.assert_called_once_with(device)
        mock_bring_online.assert_called_once_with(device)
        mock_is_dasdeckd_device.assert_called_once_with(device)
        mock_is_dasdeckd_persisted.assert_called_once_with(device)
        mock_persist_dasdeckd_device.assert_called_once_with(device)
        # mock_rollback.commitAll.assert_called_once_with()
        # Fix me mock rollback fails


class DeviceOfflineUnitTests(unittest.TestCase):
    """
    Unit tests for _device_offline() method
    """
    @mock.patch('model.storagedevices._unpersist_dasdeckd_device',
                autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_persisted', autospec=True)
    @mock.patch('model.storagedevices._is_dasdeckd_device', autospec=True)
    @mock.patch('model.storagedevices.RollbackContext', autospec=True)
    @mock.patch('model.storagedevices._is_online', autospec=True)
    @mock.patch('model.storagedevices._bring_offline', autospec=True)
    def test_device_offline_success(self, mock_bring_offline, mock_is_online,
                                    mock_rollback, mock_is_dasdeckd_device,
                                    mock_is_dasdeckd_persisted,
                                    mock_unpersist_dasdeckd_device):
        """
        unit test to validate device_offline with success scenario
        :param mock_bring_offline: mock of _bring_offline()
        of model.storagedevices
        :param mock_is_online: mock of _is_online() of model.storagedevices
        :param mock_rollback: mock of wok.rollbackcontext imported as
                        RollbackContext in model.storagedevices
        :param mock_is_dasdeckd_device : mock of
         _is_dasdeckd_device() of model.storagedevices
        :param mock_is_dasdeckd_persisted : mock of
        _is_dasdeckd_persisted() of model.storagedevices
        :param mock_unpersist_dasdeckd_device : mock of
         _unpersist_dasdeckd_device() of model.storagedevices
        on success device_offline() method doesn't return anything
        """
        device = 'dummy_device'
        mock_is_online.return_value = True
        mock_is_dasdeckd_device.return_value = True
        mock_is_dasdeckd_persisted.return_value = True
        _device_offline(device)
        mock_is_online.assert_called_once_with(device)
        mock_bring_offline.assert_called_once_with(device)
        mock_is_dasdeckd_device.assert_called_once_with(device)
        mock_is_dasdeckd_persisted.assert_called_once_with(device)
        mock_unpersist_dasdeckd_device.assert_called_once_with(device)
        # mock_rollback.commitAll.assert_called_once_with()
        # Fix me mock rollback fails


class GetDasdEckdDevicesUnitTests(unittest.TestCase):
    """
    Unit tests for _get_dasd_eckd_device() method
    """
    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_dasdeckd_devices_success(self, mock_utils):
        """
        unit test to validate get_dasdeckd_devices with success scenario
        mock_utils: mock of model_utils imported as
                    utils in model.storagedevices
        get_dasdeckd_devices should return list of outputs returned by
        utils.get_dirname() which is not None or empty string
        """
        mock_utils.get_directories.return_value = ['/path1/device1',
                                                   'path1/device2',
                                                   '']
        mock_utils.get_dirname.side_effect = ["device1", "device2", '']
        expected_out = ['device1', 'device2']
        actual_out = _get_dasdeckd_devices()
        mock_utils.get_directories.assert_called_once_with(syspath_eckd)
        calls_get_dirname = [('/path1/device1',),
                             ('path1/device2',),
                             ('',)]
        for i in range(0, 2):
            x, y = mock_utils.get_dirname.call_args_list[i]
            assert x == calls_get_dirname[i]
        assert mock_utils.get_dirname.call_count == 3
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_dasdeckd_devices_empty_dir(self, mock_utils):
        """
        unit test to validate get_dasdeckd_devices with
        get_directories of model_utils returning empty list
        mock_utils: mock of model_utils imported as
                    utils in model.storagedevices
        get_dasdeckd_devices should return empty list
        """
        mock_utils.get_directories.return_value = []
        expected_out = []
        actual_out = _get_dasdeckd_devices()
        mock_utils.get_directories.assert_called_once_with(syspath_eckd)
        self.assertFalse(mock_utils.get_dirname.called,
                         msg='Unexpected call to mock_utils.get_dirname()')
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_dasdeckd_devices_withnoneout_get_dirname(self, mock_utils):
        """
        unit test to validate get_dasdeckd_devices with
        get_dirname of model_utils returning None
        mock_utils: mock of model_utils imported as
                    utils in model.storagedevices
        get_dasdeckd_devices should return empty list
        """
        mock_utils.get_directories.return_value = ['dummy_path']
        mock_utils.get_dirname.return_value = None
        expected_out = []
        actual_out = _get_dasdeckd_devices()
        mock_utils.get_directories.assert_called_once_with(syspath_eckd)
        mock_utils.get_dirname.assert_called_once_with('dummy_path')
        self.assertEqual(actual_out, expected_out)


class GetzFCPDevicesUnitTests(unittest.TestCase):
    """
    Unit tests for _get_zfcp_device() method
    """
    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_zfcp_devices_success(self, mock_utils):
        """
        unit test to validate get_zfcp_devices with success scenario
        mock_utils: mock of model_utils imported as
                    utils in model.storagedevices
        get_zfcp_devices should return list of outputs returned by
        utils.get_dirname() which is not None or empty string
        """
        mock_utils.get_directories.return_value = ['/path1/device1',
                                                   'path1/device2',
                                                   '']
        mock_utils.get_dirname.side_effect = ["device1", "device2", '']
        expected_out = ['device1', 'device2']
        actual_out = _get_zfcp_devices()
        mock_utils.get_directories.assert_called_once_with(syspath_zfcp)
        calls_get_dirname = [('/path1/device1',),
                             ('path1/device2',),
                             ('',)]
        for i in range(0, 2):
            x, y = mock_utils.get_dirname.call_args_list[i]
            assert x == calls_get_dirname[i]
        assert mock_utils.get_dirname.call_count == 3
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_zfcp_devices_withempty_ofget_directories(self, mock_utils):
        """
        unit test to validate get_zfcp_devices with
        get_directories of model_utils returning empty list
        mock_utils: mock of model_utils imported as
                    utils in model.storagedevices
        get_zfcp_devices should return empty list
        """
        mock_utils.get_directories.return_value = []
        expected_out = []
        actual_out = _get_zfcp_devices()
        mock_utils.get_directories.assert_called_once_with(syspath_zfcp)
        self.assertFalse(mock_utils.get_dirname.called,
                         msg='Unexpected call to mock_utils.get_dirname()')
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.storagedevices.utils', autospec=True)
    def test_get_zfcp_devices_withnoneout_get_dirname(self, mock_utils):
        """
        unit test to validate get_zfcp_devices with
        get_dirname of model_utils returning None
        mock_utils: mock of model_utils imported as
                    utils in model.storagedevices
        get_zfcp_devices should return empty list
        """
        mock_utils.get_directories.return_value = ['dummy_path']
        mock_utils.get_dirname.return_value = None
        expected_out = []
        actual_out = _get_zfcp_devices()
        mock_utils.get_directories.assert_called_once_with(syspath_zfcp)
        mock_utils.get_dirname.assert_called_once_with('dummy_path')
        self.assertEqual(actual_out, expected_out)


class IsOnlineUnitTests(unittest.TestCase):
    """
    Unit tests for _is_online() method
    """
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_is_online_success(self, mock_os):
        """
        unit test to validate is_online success scenario
        (i,e, os.access returns True and device is online)
        mock_os: mock of os module imported in model.storagedevices
        On success _is_online() method returns True
        """
        device = "0.0.ffff"
        mock_os.access.return_value = True
        open_mock = mock.mock_open(read_data='1')
        with mock.patch('model.storagedevices.open', open_mock, create=True):
            actual_out = _is_online(device)
            online_file = '/sys/bus/ccw/devices/0.0.ffff/online'
            mock_os.access.assert_called_once_with(online_file, mock_os.R_OK)
            self.assertTrue(actual_out)
            open_mock.assert_called_with(
                '/sys/bus/ccw/devices/0.0.ffff/online')

    @mock.patch('model.storagedevices.os', autospec=True)
    def test_is_online_device_offline(self, mock_os):
        """
        unit test to validate is_online returning False(ie,
        device is offline)
        mock_os: mock of os module imported in model.storagedevices
        _is_online() method returns False
        """
        mock_os.access.return_value = True
        open_mock = mock.mock_open(read_data='0')
        with mock.patch('model.storagedevices.open', open_mock, create=True):
            status = _is_online('0.0.ffff')
            online_file = '/sys/bus/ccw/devices/0.0.ffff/online'
            mock_os.access.assert_called_once_with(online_file, mock_os.R_OK)
            open_mock.assert_called_with(
                '/sys/bus/ccw/devices/0.0.ffff/online')
            self.assertFalse(status)

    @mock.patch('model.storagedevices.os', autospec=True)
    def test_is_online_no_access(self, mock_os):
        """
        unit test to validate is_online with no access to online file
        _is_online() method should return False
        """
        mock_os.access.return_value = False
        open_mock = mock.mock_open(read_data='0')
        with mock.patch('model.storagedevices.open', open_mock, create=True):
            status = _is_online('0.0.ffff')
            self.assertFalse(open_mock.called,
                             msg='Unexpected call to open_mock()')
            self.assertEqual(status, False)


class IsDasdEckdPersistedUnitTests(unittest.TestCase):
    """
    Unit tests for _is_dasdeckd_persisted()
    """
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_device_persistsed(self, mock_os):
        """
        unit test to validate _is_dasdeckd_persisted() method
        success scenario(ie, dasd-eckd device is persisted and
        user has read access to /etc/dasd.conf)
        mock_os: mock python os module imported in model.storagedevices
        on scuccess, _is_dasdeckd_persisted() should return True
        """
        device = "dummy_device"
        mock_os.access.return_value = True
        open_mock = mock.mock_open(read_data='dummy_device')
        with mock.patch('model.storagedevices.open', open_mock, create=True):
            status = _is_dasdeckd_persisted(device)
            mock_os.access.assert_called_once_with(DASD_CONF, mock_os.R_OK)
            self.assertTrue(status)
            open_mock.assert_called_once_with(DASD_CONF)

    @mock.patch('model.storagedevices.os', autospec=True)
    def test_device_not_persistsed(self, mock_os):
        """
        unit test to validate _is_dasdeckd_persisted() method for a
        device which is not persisted
        mock_os: mock python os module imported in model.storagedevices
        _is_dasdeckd_persisted() should return False
        """
        device = "dummy_device"
        mock_os.access.return_value = True
        open_mock = mock.mock_open(read_data='No Content')
        with mock.patch('model.storagedevices.open', open_mock, create=True):
            status = _is_dasdeckd_persisted(device)
            mock_os.access.assert_called_once_with(DASD_CONF, mock_os.R_OK)
            self.assertFalse(status)
            open_mock.assert_called_once_with(DASD_CONF)

    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persisted_no_access(self, mock_os):
        """
        unit test to validate _is_dasdeckd_persisted() method
        failure scenario(os.acces returns False ie.,
        failed to access /etc/dasd.conf file)
        mock_os: mock python os module imported in model.storagedevices
        _is_dasdeckd_persisted() should return False
        """
        device = "dummy_device"
        mock_os.access.return_value = False
        open_mock = mock.mock_open(read_data='No Content')
        with mock.patch('model.storagedevices.open', open_mock, create=True):
            status = _is_dasdeckd_persisted(device)
            mock_os.access.assert_called_once_with(DASD_CONF, mock_os.R_OK)
            self.assertFalse(status)
            self.assertFalse(open_mock.called,
                             msg='Unexpected call to open_mock()')


class IsDasdEckdDeviceUnitTests(unittest.TestCase):
    """
    Unit tests for _is_dasdeckd_device() method
    """
    @mock.patch('model.storagedevices._get_dasdeckd_devices', autospec=True)
    def test_is_dasdeckd_success(self, mock_get_dasdeckd_devices):
        """
        unit test to validate if device is of type dasd-eckd - success
        scenario (ie, given device is of type dasd-eckd)
        mock_get_dasdeckd_devices: mock of _get_dasdeckd_devices
        model.storagedevices
        on success _is_dasdeckd_device() returns True
        """
        mock_get_dasdeckd_devices.return_value = ['dummy_device', 'device2']
        expected_out = True
        device = 'dummy_device'
        actual_out = _is_dasdeckd_device(device)
        mock_get_dasdeckd_devices.assert_called_once_with()
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.storagedevices._get_dasdeckd_devices', autospec=True)
    def test_is_dasdeckd_failure(self, mock_get_dasdeckd_devices):
        """
        unit test to validate if device is of type dasd-eckd - failure
        scenario (ie, given device is not of dasd-eckd type)
        mock_get_dasdeckd_devices: mock of _get_dasdeckd_devices
        model.storagedevices
        on failure _is_dasdeckd_device() returns False
        """
        mock_get_dasdeckd_devices.return_value = ['dummy_device', 'device2']
        expected_out = False
        device = 'dev_not'
        actual_out = _is_dasdeckd_device(device)
        mock_get_dasdeckd_devices.assert_called_once_with()
        self.assertEqual(actual_out, expected_out)


class IszFCPDeviceUnitTests(unittest.TestCase):
    """
    unit tests for _is_zfcp_device() method
    """
    @mock.patch('model.storagedevices._get_zfcp_devices', autospec=True)
    def test_is_zfcp_success(self, mock_get_zfcp_devices):
        """
        unit test to validate if device is of type zfcp - success
        scenario (ie, given device is of type zfcp)
        mock_get_zfcp_devices: mock of _get_zfcp_devices model.storagedevices
        on success _is_zfcp_device() returns True
        """
        mock_get_zfcp_devices.return_value = ['dummy_device', 'device2']
        expected_out = True
        device = 'dummy_device'
        actual_out = _is_zfcp_device(device)
        mock_get_zfcp_devices.assert_called_once_with()
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.storagedevices._get_zfcp_devices', autospec=True)
    def test_is_zfcp_failure(self, mock_get_zfcp_devices):
        """
        unit test to validate if device is of type zfcp - failure
        scenario (ie, given device is not of zfcp type)
        mock_get_zfcp_devices: mock of _get_zfcp_devices model.storagedevices
        on failure _is_zfcp_device() returns False
        """
        mock_get_zfcp_devices.return_value = ['dummy_device', 'device2']
        expected_out = False
        device = 'dev_not'
        actual_out = _is_zfcp_device(device)
        mock_get_zfcp_devices.assert_called_once_with()
        self.assertEqual(actual_out, expected_out)


class PersistDasdEckdDeviceUnitTests(unittest.TestCase):
    """
    unit tests for _persist_dasdeckd_device() method
    """
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persist_dasdeckd_success(self, mock_os):
        """
        unit test to validate persisting dasd-eckd device, success
        scenario(os.system return code is 0)
        mock_os: mock of python os module imported in storagedevices
        on success, _persist_dasdeckd_device() method doesn't return anything
        """
        mock_os.system.return_value = 0
        mock_os.access.return_value = True
        device = "dummy_device"
        command = 'flock -w 1 %s -c \"echo %s >> %s\"' \
                  % (DASD_CONF, device, DASD_CONF)
        _persist_dasdeckd_device(device)
        mock_os.access.assert_called_once_with(DASD_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persist_dasdeckd_failtowrite_tofile(self, mock_os, mock_log):
        """
        unit test to validate persisting dasd-eckd device, failure
        scenario(os.system return code is not zero)
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _persist_dasdeckd_device() raises OperationFailed exception
        """
        mock_os.system.return_value = 1
        mock_os.access.return_value = True
        device = "dummy_device"
        command = 'flock -w 1 %s -c \"echo %s >> %s\"' \
                  % (DASD_CONF, device, DASD_CONF)
        self.assertRaises(exception.OperationFailed,
                          _persist_dasdeckd_device, device)
        mock_os.access.assert_called_once_with(DASD_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)
        mock_log.error.assert_called_with("Failed to persist "
                                          "dasd-eckd device: %s" % device)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persist_dasdeckd_failtoaccess_file(self, mock_os, mock_log):
        """
        unit test to validate persisting dasd-eckd device, failure
        scenario(os.accsess returns False, ie, failed to
        access dasd.conf file in write mode)
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _persist_dasdeckd_device() raises OperationFailed exception
        """
        mock_os.access.return_value = False
        device = "dummy_device"
        self.assertRaises(exception.OperationFailed,
                          _persist_dasdeckd_device, device)
        mock_os.access.assert_called_once_with(DASD_CONF, mock_os.W_OK)
        self.assertFalse(mock_os.system.called,
                         msg='Unexpected call to mock_os.system()')
        mock_log.error.assert_called_with("Failed to persist "
                                          "dasd-eckd device: %s" % device)


class UnPersistDasdEckdUnitTests(unittest.TestCase):
    """
    unit tests for _unpersist_dasdeckd_device() method
    """
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_unpersist_dasdeckd_success(self, mock_os):
        """
        unit test to validate un persisting dasd-eckd
        device(removing dasd-eckd device id from dasd.conf file),
        success scenario(os.system return code is 0)
        mock_os: mock of python os module imported in storagedevices
        on success, _unpersist_dasdeckd_device()
         method doesn't return anything
        """
        mock_os.system.return_value = 0
        mock_os.access.return_value = True
        device = "dummy_device"
        command = 'flock -w 1 %s -c \"sed -i \'/%s/Id\' %s\"' \
                  % (DASD_CONF, device, DASD_CONF)
        _unpersist_dasdeckd_device(device)
        mock_os.access.assert_called_once_with(DASD_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_unpersist_dasdeckd_failtowrite_tofile(self, mock_os, mock_log):
        """
        unit test to validate un persisting dasd-eckd device, failure
        scenario(os.system return code is not zero)
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _unpersist_dasdeckd_device()
        raises OperationFailed exception
        """
        mock_os.system.return_value = 1
        mock_os.access.return_value = True
        device = "dummy_device"
        command = 'flock -w 1 %s -c \"sed -i \'/%s/Id\' %s\"' \
                  % (DASD_CONF, device, DASD_CONF)
        self.assertRaises(exception.OperationFailed,
                          _unpersist_dasdeckd_device, device)
        mock_os.access.assert_called_once_with(DASD_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)
        mock_log.error.assert_called_with("Failed to unpersist"
                                          " dasd-eckd device: %s" % device)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_unpersist_dasdeckd_failtoaccess_file(self, mock_os, mock_log):
        """
        unit test to validate un persisting dasd-eckd device, failure
        scenario - os.accsess returns False, ie, failed to
        access dasd.conf file in write mode
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _unpersist_dasdeckd_device()
        raises OperationFailed exception
        """
        mock_os.access.return_value = False
        device = "dummy_device"
        self.assertRaises(exception.OperationFailed,
                          _unpersist_dasdeckd_device, device)
        mock_os.access.assert_called_once_with(DASD_CONF, mock_os.W_OK)
        mock_log.error.assert_called_with("Failed to unpersist "
                                          "dasd-eckd device: %s" % device)
        self.assertFalse(mock_os.system.called,
                         msg='Unexpected call to mock_os.system()')


class BringOnlineUnitTests(unittest.TestCase):
    """
    unit tests for _bring_online() method
    """
    @mock.patch('model.storagedevices.run_command', autospec=True)
    def test_bring_online_success(self, mock_run_command):
        """
        unit test to validate bring device online, success
        scenario(run_command return code is 0)
        mock_run_command: mock of wok.utils.run_command imported
                        in model.storagedevices
        on success _bring_online() method doesn't return anything
        """
        mock_run_command.return_value = ["", "", 0]
        device = "dummy_device"
        command = ["chccwdev", '-e', device]
        _bring_online(device)
        mock_run_command.assert_called_once_with(command)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    def test_bring_online_failure(self, mock_run_command, mock_log):
        """
        unit test to validate bring device online, failure
        scenario(run_command return code is not zero)
        mock_run_command: mock of wok.utils.run_command imported
                          in model.storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure _bring_online() should raise OperationFailed exception
        """
        mock_run_command.return_value = ["", "dummy error", 1]
        device = "dummy_device"
        command = ["chccwdev", '-e', device]
        self.assertRaises(exception.OperationFailed, _bring_online, device)
        mock_run_command.assert_called_once_with(command)
        mock_log.error.assert_called_with("Failed to bring device %s online."
                                          " Error: dummy error" % device)


class BringOfflineUnitTests(unittest.TestCase):
    """
    unit tests for _bring_offline() method
    """
    @mock.patch('model.storagedevices.run_command', autospec=True)
    def test_bring_offline_success(self, mock_run_command):
        """
        unit test to validate bring device offline, success
        scenario(run_command return code is 0)
        mock_run_command: mock of wok.utils.run_command imported
                          in model.storagedevices
        on success _bring_offline() method doesn't return anything
        """
        mock_run_command.return_value = ["", "", 0]
        device = "dummy_device"
        command = ["chccwdev", '-d', device]
        _bring_offline(device)
        mock_run_command.assert_called_once_with(command)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.run_command', autospec=True)
    def test_bring_offline_failure(self, mock_run_command, mock_log):
        """
        unit test to validate bring device offline, failure
        scenario(run_command return code is not zero)
        mock_run_command: mock of wok.utils.run_command imported
                          in model.storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure _bring_offline() should raise OperationFailed exception
        """
        mock_run_command.return_value = ["", "dummy error", 1]
        device = "dummy_device"
        command = ["chccwdev", '-d', device]
        self.assertRaises(exception.OperationFailed, _bring_offline, device)
        mock_run_command.assert_called_once_with(command)
        mock_log.error.assert_called_with("Failed to bring device %s offline."
                                          " Error: dummy error" % device)


class PersistZFCPDeviceUnitTests(unittest.TestCase):
    """
    unit tests for _persist_zfcp_device() method
    """
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persist_zfcp_success(self, mock_os):
        """
        unit test to validate persisting zfcp device, success
        scenario(os.system return code is 0)
        mock_os: mock of python os module imported in storagedevices
        on success, _persist_zfcp_device() method doesn't return anything
        """
        mock_os.system.return_value = 0
        mock_os.access.return_value = True
        device = "dummy_device"
        persist_data = device + ' 0x0000000000000000 0x0000000000000000'
        command = 'flock -w 1 %s -c \"echo %s >> %s\"' \
                  % (ZFCP_CONF, persist_data, ZFCP_CONF)
        _persist_zfcp_device(device)
        mock_os.access.assert_called_once_with(ZFCP_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persist_zfcp_failtowrite_tofile(self, mock_os, mock_log):
        """
        unit test to validate persisting zfcp device, failure
        scenario(os.system return code is not zero)
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _persist_zfcp_device() raises OperationFailed exception
        """
        mock_os.system.return_value = 1
        mock_os.access.return_value = True
        device = "dummy_device"
        persist_data = device + ' 0x0000000000000000 0x0000000000000000'
        command = 'flock -w 1 %s -c \"echo %s >> %s\"' \
                  % (ZFCP_CONF, persist_data, ZFCP_CONF)
        self.assertRaises(exception.OperationFailed,
                          _persist_zfcp_device, device)
        mock_os.access.assert_called_once_with(ZFCP_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)
        mock_log.error.assert_called_with("Failed to persist "
                                          "zfcp device: %s" % device)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_persist_zfcp_failtoaccess_file(self, mock_os, mock_log):
        """
        unit test to validate persisting zfcp device, failure
        scenario(os.accsess returns False, ie, failed to
        access zfcp.conf file in write mode)
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _persist_zfcp_device() raises OperationFailed exception
        """
        mock_os.access.return_value = False
        device = "dummy_device"
        self.assertRaises(exception.OperationFailed,
                          _persist_zfcp_device, device)
        mock_os.access.assert_called_once_with(ZFCP_CONF, mock_os.W_OK)
        self.assertFalse(mock_os.system.called,
                         msg='Unexpected call to mock_os.system()')
        mock_log.error.assert_called_with("Failed to persist "
                                          "zfcp device: %s" % device)


class UnPersistZFCPUnitTests(unittest.TestCase):
    """
    unit tests for _unpersist_zfcp_device() method
    """
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_unpersist_zfcp_success(self, mock_os):
        """
        unit test to validate un persisting zfcp
        device(removing zfcp device id from zfcp.conf file),
        success scenario(os.system return code is 0)
        mock_os: mock of python os module imported in storagedevices
        on success, _unpersist_zfcp_device()
        method doesn't return anything
        """
        mock_os.system.return_value = 0
        mock_os.access.return_value = True
        device = "dummy_device"
        command = 'flock -w 1 %s -c \"sed -i \'/%s/Id\' %s\"' \
                  % (ZFCP_CONF, device, ZFCP_CONF)
        _unpersist_zfcp_device(device)
        mock_os.access.assert_called_once_with(ZFCP_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_unpersist_zfcp_failtowrite_tofile(self, mock_os, mock_log):
        """
        unit test to validate un persisting zfcp device, failure
        scenario(os.system return code is not zero)
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _unpersist_zfcp_device()
        raises OperationFailed exception
        """
        mock_os.system.return_value = 1
        mock_os.access.return_value = True
        device = "dummy_device"
        command = 'flock -w 1 %s -c \"sed -i \'/%s/Id\' %s\"' \
                  % (ZFCP_CONF, device, ZFCP_CONF)
        self.assertRaises(exception.OperationFailed,
                          _unpersist_zfcp_device, device)
        mock_os.access.assert_called_once_with(ZFCP_CONF, mock_os.W_OK)
        mock_os.system.assert_called_once_with(command)
        mock_log.error.assert_called_with("Failed to unpersist"
                                          " zfcp device: %s" % device)

    @mock.patch('model.storagedevices.wok_log', autospec=True)
    @mock.patch('model.storagedevices.os', autospec=True)
    def test_unpersist_zfcp_failtoaccess_file(self, mock_os, mock_log):
        """
        unit test to validate un persisting zfcp device, failure
        scenario - os.accsess returns False, ie, failed to
        access zfcp.conf file in write mode
        mock_os: mock of python os module imported in storagedevices
        mock_log: mock of wok_log imported in model.storagedevices
        on failure, _unpersist_zfcp_device()
        raises OperationFailed exception
        """
        mock_os.access.return_value = False
        device = "dummy_device"
        self.assertRaises(exception.OperationFailed,
                          _unpersist_zfcp_device, device)
        mock_os.access.assert_called_once_with(ZFCP_CONF, mock_os.W_OK)
        mock_log.error.assert_called_with("Failed to unpersist "
                                          "zfcp device: %s" % device)
        self.assertFalse(mock_os.system.called,
                         msg='Unexpected call to mock_os.system()')
