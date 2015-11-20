#
# Project Ginger S390x
#
# Copyright IBM, Corp. 2015
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
from model.storagedevices import _byte_to_binary, _format_lscss
from model.storagedevices import _get_deviceinfo, _get_paths
from model.storagedevices import _hex_to_binary, _list_devicesinfo
from model.storagedevices import StorageDeviceModel, StorageDevicesModel


syspath_eckd = "/sys/bus/ccw/drivers/dasd-eckd/0.*/"
syspath_zfcp = "/sys/bus/ccw/drivers/zfcp/0.*/"
DASD_CONF = '/etc/dasd.conf'


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
        mock_utils.get_directories.return_value = ["abc"]
        mock_run_command.return_value = ["", "", 0]
        self.assertRaises(exception.InvalidParameter,
                          storagedevicesmodel.get_list, 'abc')
        mock_utils.get_directories.assert_not_called()
        mock_log.error.assert_called_with("Invalid _type given. _type: abc")

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
        mock_run_command.return_value = ["dummyout", "", 0]
        mock_is_dasdeckd_device.return_value = True
        mock_is_zfcp_device.return_value = False
        mock_validate_device.return_value = "dummydevice"
        mock_get_deviceinfo.return_value = {'dummydevice': 'dummyout'}
        storagedevicemodel = StorageDeviceModel()
        return_value = storagedevicemodel.get_storagedevice('dummydevice')
        mock_run_command.assert_called_once_with(command)
        mock_get_deviceinfo.assert_called_once_with('dummyout', "dummydevice")
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
