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
import re
import unittest

import wok.exception as exception
from model.nwdevices import _bring_offline, _bring_online
from model.nwdevices import _configure_interface, _create_ifcfg_file
from model.nwdevices import _format_znetconf, _get_configured_devices
from model.nwdevices import _get_unconfigured_devices, _is_interface_online
from model.nwdevices import NetworkDeviceModel, NetworkDevicesModel
from model.nwdevices import _persist_interface
from model.nwdevices import _unconfigure_interface, _unpersist_interface
from model.nwdevices import _validate_device, _write_ifcfg_params

ifcfg_path = 'etc/sysconfig/network-scripts/ifcfg-enccw<deviceid>'

ZNETCONF_DEV_IDS = "Device IDs"
ZNETCONF_TYPE = "Type"
ZNETCONF_CARDTYPE = "Card Type"
ZNETCONF_CHPID = "CHPID"
ZNETCONF_DRV = "Drv"
ZNETCONF_DEV_NAME = "Name"
ZNETCONF_STATE = "State"
UNIQUE_COL_NAME = "name"
ENCCW = 'enccw'

UNCONF_HDR_PATTERN = r'('+re.escape(ZNETCONF_DEV_IDS) + r')\s+' \
                     r'('+re.escape(ZNETCONF_TYPE) + r')\s+' \
                     r'('+re.escape(ZNETCONF_CARDTYPE) + r')\s+' \
                     r'('+re.escape(ZNETCONF_CHPID) + r')\s+' \
                     r'('+re.escape(ZNETCONF_DRV) + r')\.\s+$'

CONF_HDR_PATTERN = r'('+re.escape(ZNETCONF_DEV_IDS) + r')\s+' \
                   r'('+re.escape(ZNETCONF_TYPE) + r')\s+' \
                   r'('+re.escape(ZNETCONF_CARDTYPE) + r')\s+' \
                   r'('+re.escape(ZNETCONF_CHPID) + r')\s+' \
                   r'('+re.escape(ZNETCONF_DRV) + r')\.\s+' \
                   r'('+re.escape(ZNETCONF_DEV_NAME) + r')\s+' \
                   r'('+re.escape(ZNETCONF_STATE) + r')\s+$'

CONF_DEVICE_PATTERN = r'(\d\.\d\.[0-9a-fA-F]{4},' \
                      r'\d\.\d\.[0-9a-fA-F]{4},' \
                      r'\d\.\d\.[0-9a-fA-F]{4})\s+' \
                      r'(\w+\/\w+)\s+' \
                      r'(\w+)\s+' \
                      r'([0-9a-fA-F]{2})\s+' \
                      r'(qeth)\s+' \
                      r'(\w+\d\.\d\.[0-9a-fA-F]{4})\s+' \
                      r'(\w+)\s{0,}$'

UNCONF_DEVICE_PATTERN = r'(\d\.\d\.[0-9a-fA-F]{4},' \
                        r'\d\.\d\.[0-9a-fA-F]{4},' \
                        r'\d\.\d\.[0-9a-fA-F]{4})\s+' \
                        r'(\w+\/\w+)\s+' \
                        r'(OSA\s+\(\w+\))\s+' \
                        r'([0-9a-fA-F]{2})\s+' \
                        r'(qeth)\s{0,}$'


class GetListUnitTests(unittest.TestCase):
    """
    unit tests for get_list() method of NetworkDevicesModel()
    using mock module
    """
    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices.wok_log')
    def test_invalid_configured(self, mock_wok_log,
                                mock_get_unconfigured_devices,
                                mock_get_configured_devices):
        """
        unit test to validate get_list() method of NetworkDevicesModel()
        with invalid value for _configured param
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        get_list() should raise InvalidParameter Exception
        """
        configured = 'invalid'
        networkdevicesmodel = NetworkDevicesModel()
        self.assertRaises(exception.InvalidParameter,
                          networkdevicesmodel.get_list, configured)
        self.assertFalse(mock_get_configured_devices.called, msg='Unexpected'
                         ' call to mock_get_configured_devices')
        self.assertFalse(mock_get_unconfigured_devices.called,
                         msg='Unexpected call to mock_get_configured_devices')
        mock_wok_log.error.assert_called_once_with("Invalid _configured "
                                                   "given. _configured: "
                                                   "%s" % configured)

    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices.wok_log')
    def test_confugred_true(self, mock_wok_log,
                            mock_get_unconfigured_devices,
                            mock_get_configured_devices):
        """
        unit test to validate get_list() method of NetworkDevicesModel()
        with true/True value for _configured param
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        get_list() should call only _get_configured_devices() method
        """
        configured = 'True'
        networkdevicesmodel = NetworkDevicesModel()
        mock_get_configured_devices.return_value = ['dummy_device']
        expected_out = ['dummy_device']
        actual_out = networkdevicesmodel.get_list(configured)
        mock_get_configured_devices.assert_called_once_with()
        self.assertFalse(mock_get_unconfigured_devices.called,
                         msg='Unexpected call to mock_get_configured_devices')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to'
                        ' mock_wok_log.info(). Not called')
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices.wok_log')
    def test_confugred_false(self, mock_wok_log,
                             mock_get_unconfigured_devices,
                             mock_get_configured_devices):
        """
        unit test to validate get_list() method of NetworkDevicesModel()
        with false/False value for _configured param
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        get_list() should call only _get_unconfigured_devices() method
        """
        configured = 'False'
        networkdevicesmodel = NetworkDevicesModel()
        mock_get_unconfigured_devices.return_value = ['dummy_device']
        expected_out = ['dummy_device']
        actual_out = networkdevicesmodel.get_list(configured)
        mock_get_unconfigured_devices.assert_called_once_with()
        self.assertFalse(mock_get_configured_devices.called,
                         msg='Unexpected call to mock_get_configured_devices')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to'
                        ' mock_wok_log.info(). Not called')
        self.assertEqual(actual_out, expected_out)

    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_without_confugred(self, mock_wok_log,
                               mock_get_unconfigured_devices,
                               mock_get_configured_devices):
        """
        unit test to validate get_list() method of NetworkDevicesModel()
        without passing any value for _configured param

        mock_wok_log: mock of wok_log of model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        get_list() should call _get_configured_devices() and
        _get_unconfigured_devices()
        """
        configured = None
        networkdevicesmodel = NetworkDevicesModel()
        mock_get_configured_devices.return_value = ['dummy_device1']
        mock_get_unconfigured_devices.return_value = ['dummy_device2']
        expected_out = ['dummy_device1', 'dummy_device2']
        actual_out = networkdevicesmodel.get_list(configured)
        mock_get_unconfigured_devices.assert_called_once_with()
        mock_get_configured_devices.assert_called_once_with()
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to'
                        ' mock_wok_log.info(). Not called')
        self.assertEqual(actual_out, expected_out)


class NetworkDeviceLookUpUnitTests(unittest.TestCase):
    """
    unit tests for lookup() method of NetworkDeviceModel using mock module
    """
    @mock.patch('model.nwdevices.TaskModel', autospec=True)
    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices._validate_device', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_invalid_device_type(self, mock_wok_log, mock_validate_device,
                                 mock_get_unconfigured_devices,
                                 mock_get_configured_devices, mock_task_model):
        """
        unit test to validate lookup() of NetworkDeviceModel() model with
        invalid device type(ie, the device is not of type OSA)
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_validate_device: mock of _validate_device() method
                              in model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.nwdevices

        lookup() should raise InvalidParameter exception
        """
        device = 'dummy_device'
        mock_get_unconfigured_devices.return_value = {'device1': 'dummy_data'}
        mock_get_configured_devices.return_value = {'device2': 'dummy_data'}
        nwmodel = NetworkDeviceModel(kargs=None)
        self.assertRaises(exception.InvalidParameter, nwmodel.lookup, device)
        mock_validate_device.assert_called_once_with(device)
        mock_get_configured_devices.assert_called_once_with(UNIQUE_COL_NAME)
        mock_get_unconfigured_devices.assert_called_once_with(UNIQUE_COL_NAME)
        mock_wok_log.error.assert_called_once_with('Given device is not '
                                                   'of type OSA. Device: '
                                                   '%s', device)

    @mock.patch('model.nwdevices.TaskModel', autospec=True)
    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices._validate_device', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_validate_exception(self, mock_wok_log, mock_validate_device,
                                mock_get_unconfigured_devices,
                                mock_get_configured_devices, mock_task_model):
        """
        unit test to validate lookup() of NetworkDeviceModel() model with
        _validate_device() raising  an exception
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_validate_device: mock of _validate_device() method
                              in model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.nwdevices

        lookup() should raise same exception raised by _validate_device()
        """
        device = 'dummy_device'
        mock_validate_device.side_effect = SyntaxError('dummy_error')
        # picking random error
        nwmodel = NetworkDeviceModel(kargs=None)
        self.assertRaises(SyntaxError, nwmodel.lookup, device)
        self.assertFalse(mock_get_configured_devices.called, msg='Unexpected'
                         ' call to mock_get_configured_devices()')
        self.assertFalse(mock_get_unconfigured_devices.called, msg='Unexpected'
                         ' call to mock_get_unconfigured_devices()')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.TaskModel', autospec=True)
    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices._validate_device', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_configured_device(self, mock_wok_log, mock_validate_device,
                               mock_get_unconfigured_devices,
                               mock_get_configured_devices, mock_task_model):
        """
        unit test to validate lookup() of NetworkDeviceModel() model with
        device which is in configured devices
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_validate_device: mock of _validate_device() method
                              in model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.nwdevices

        lookup() should output returned from _get_configured_devices()
        """
        device = 'dummy_device'
        expected_out = {device: 'device_found'}
        mock_get_configured_devices.return_value = expected_out
        nwmodel = NetworkDeviceModel(kargs=None)
        actual_out = nwmodel.lookup(device)
        mock_validate_device.assert_called_once_with(device)
        mock_get_configured_devices.assert_called_once_with(UNIQUE_COL_NAME)
        self.assertFalse(mock_get_unconfigured_devices.called,
                         msg='Unexpected call to '
                             'mock_get_unconfigured_devices()')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        self.assertEqual(actual_out, expected_out[device])

    @mock.patch('model.nwdevices.TaskModel', autospec=True)
    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices._get_unconfigured_devices', autospec=True)
    @mock.patch('model.nwdevices._validate_device', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_unconfigured_device(self, mock_wok_log, mock_validate_device,
                                 mock_get_unconfigured_devices,
                                 mock_get_configured_devices, mock_task_model):
        """
        unit test to validate lookup() of NetworkDeviceModel() model with
        device which is in unconfigured devices
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_validate_device: mock of _validate_device() method
                              in model.nwdevices
        mock_get_unconfigured_devices: mock of _get_unconfigured_devices()
                                       method in model.nwdevices()
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.nwdevices

        lookup() should output returned from _get_unconfigured_devices()
        """
        device = 'dummy_device'
        expected_out = {device: 'device_found'}
        mock_get_configured_devices.return_value = {'dev1': 'not_found'}
        mock_get_unconfigured_devices.return_value = expected_out
        nwmodel = NetworkDeviceModel(kargs=None)
        actual_out = nwmodel.lookup(device)
        mock_validate_device.assert_called_once_with(device)
        mock_get_configured_devices.assert_called_once_with(UNIQUE_COL_NAME)
        mock_get_unconfigured_devices.assert_called_once_with(UNIQUE_COL_NAME)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        self.assertEqual(actual_out, expected_out[device])


class PostOperationsNetworkDeviceModel(unittest.TestCase):
    """
    unit tests for post operations in NetworkDeviceModel() using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.add_task', autospec=True)
    @mock.patch('model.nwdevices.TaskModel', autospec=True)
    def test_model_configure(self, mock_taskmodel, mock_add_task,
                             mock_wok_log):
        """
        unit test to validate configure() action with success scenario
        mock_taskmodel: mock of wok.model.tasks imported as TaskModel
                        in model.nwdevices
        mock_add_task: mock of model.utils.add_task() imported
                       in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        """
        interface = 'enccw_interface'
        taskid = 1
        mock_add_task.return_value = taskid
        mock_taskmodel.lookup.return_value = "test_task"
        nwm = NetworkDeviceModel(kargs=None)
        nwm.configure(interface)
        self.assertTrue(mock_add_task.called,
                        msg='Expected call to mock_add_task(). Not Called')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.add_task', autospec=True)
    @mock.patch('model.nwdevices.TaskModel', autospec=True)
    def test_model_unconfigure(self, mock_taskmodel, mock_add_task,
                               mock_wok_log):
        """
        unit test to validate unconfigure() action with success scenario
        mock_taskmodel: mock of wok.model.tasks imported as TaskModel
                        in model.nwdevices
        mock_add_task: mock of model.utils.add_task() imported
                       in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        """
        interface = 'enccw_interface'
        taskid = 1
        mock_add_task.return_value = taskid
        mock_taskmodel.lookup.return_value = "test_task"
        nwm = NetworkDeviceModel(kargs=None)
        nwm.unconfigure(interface)
        self.assertTrue(mock_add_task.called,
                        msg='Expected call to mock_add_task(). Not Called')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')


class BringOnlineUnitTests(unittest.TestCase):
    """
    unit tests for _bring_online() method using mock
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    def test_bring_online_success(self, mock_run_command, mock_wok_log):
        """
        unit test to validate _bring_online(), success
        scenario(run_command return code is 0)
        mock_run_command: mock of wok.utils.run_command
                         imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        on success _bring_online() method doesn't return anything
        """
        mock_run_command.return_value = ["", "", 0]
        device = "dummy_device"
        command = ["znetconf", '-a', device]
        _bring_online(device)
        mock_run_command.assert_called_once_with(command)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    def test_bring_online_failure(self, mock_run_command, mock_wok_log):
        """
        unit test to validate _bring_online(), failure
        scenario(run_command return code is not zero)
        mock_run_command: mock of wok.utils.run_command
                         imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        on failure _bring_online() should raise OperationFailed exception
        """
        mock_run_command.return_value = ["", "dummy error", 1]
        device = "dummy_device"
        command = ["znetconf", '-a', device]
        self.assertRaises(exception.OperationFailed, _bring_online, device)
        mock_run_command.assert_called_once_with(command)
        mock_wok_log.error.assert_called_with('failed to configure network'
                                              ' device %s. Error: dummy '
                                              'error' % device)


class BringOfflineUnitTests(unittest.TestCase):
    """
    unit tests for _bring_offline() method using mock
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    def test_bring_offline_success(self, mock_run_command, mock_wok_log):
        """
        unit test to validate _bring_offline(), success
        scenario(run_command return code is 0)
        mock_run_command: mock of wok.utils.run_command
                         imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        on success _bring_offline() method doesn't return anything
        """
        mock_run_command.return_value = ["", "", 0]
        device = "dummy_device"
        command = ["znetconf", '-r', device, '-n']
        _bring_offline(device)
        mock_run_command.assert_called_once_with(command)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    def test_bring_offline_failure(self, mock_run_command, mock_wok_log):
        """
        unit test to validate _bring_offline(), failure
        scenario(run_command return code is not zero)
        mock_run_command: mock of wok.utils.run_command
                         imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        on failure _bring_offline() should raise OperationFailed exception
        """
        mock_run_command.return_value = ["", "dummy error", 1]
        device = "dummy_device"
        command = ["znetconf", '-r', device, '-n']
        self.assertRaises(exception.OperationFailed, _bring_offline, device)
        mock_run_command.assert_called_once_with(command)
        mock_wok_log.error.assert_called_with('failed to un-configure '
                                              'network device. Device: %s, '
                                              'Error: dummy error' % device)


class PersistInterfaceUnitTests(unittest.TestCase):
    """
    unit tests for _persist_interface() method using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    @mock.patch('model.nwdevices._write_ifcfg_params', autospec=True)
    @mock.patch('model.nwdevices._create_ifcfg_file', autospec=True)
    def test_persist_with_file(self, mock_create_ifcfg_file,
                               mock_write_ifcfg_params, mock_os,
                               mock_wok_log):
        """
        unit test to validate _persist_interface() with ifcfg
        file(ie, os.path.isfile returns True)
        mock_create_ifcfg_file: mock of _create_ifcfg_file() method
                         of model.nwdevices
        mock_write_ifcfg_params: mock of _write_ifcfg_params() method
                         of model.nwdevices
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: _persist_interface() method shouldn't call
                            _create_ifcfg_file() method
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        mock_os.path.isfile.return_value = True
        _persist_interface(device)
        mock_os.path.isfile.assert_called_once_with(ifcfg_file_path)
        mock_write_ifcfg_params.assert_called_once_with(device)
        self.assertFalse(mock_create_ifcfg_file.called, msg='Unexpected '
                         'call to mock_create_ifcfg_file()')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    @mock.patch('model.nwdevices._write_ifcfg_params', autospec=True)
    @mock.patch('model.nwdevices._create_ifcfg_file', autospec=True)
    def test_persist_without_file(self, mock_create_ifcfg_file,
                                  mock_write_ifcfg_params, mock_os,
                                  mock_wok_log):
        """
        unit test to validate _persist_interface() with no ifcfg
        file(ie, os.path.isfile returns False)
        mock_create_ifcfg_file: mock of _create_ifcfg_file() method
                         of model.nwdevices
        mock_write_ifcfg_params: mock of _write_ifcfg_params() method
                         of model.nwdevices
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: _persist_interface() method should call
                            _create_ifcfg_file() method
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        mock_os.path.isfile.return_value = False
        _persist_interface(device)
        mock_os.path.isfile.assert_called_once_with(ifcfg_file_path)
        mock_write_ifcfg_params.assert_called_once_with(device)
        mock_create_ifcfg_file.assert_called_once_with(device)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')


class UnpersistInterfaceUnitTests(unittest.TestCase):
    """
    unit tests for _unpersist_interface() method using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_unpersist_without_file(self, mock_os, mock_wok_log):
        """
        unit test to validate _unpersist_interface() without ifcfg
        file(ie, os.path.isfile returns False)
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: _unpersist_interface() method shouldn't call
                            os.remove()
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        mock_os.path.isfile.return_value = False
        _unpersist_interface(device)
        mock_os.path.isfile.assert_called_once_with(ifcfg_file_path)
        self.assertFalse(mock_os.remove.called, msg='Unexpected to call '
                         'to mock_os.remove')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_unpersist_with_file(self, mock_os, mock_wok_log):
        """
        unit test to validate _unpersist_interface() with ifcfg
        file(ie, os.path.isfile returns True)
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: _unpersist_interface() method should call
                            os.remove()
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        mock_os.path.isfile.return_value = True
        _unpersist_interface(device)
        mock_os.path.isfile.assert_called_once_with(ifcfg_file_path)
        mock_os.remove.assert_called_once_with(ifcfg_file_path)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_unpersist_exception(self, mock_os, mock_wok_log):
        """
        unit test to validate _unpersist_interface() with ifcfg
        file(ie, os.path.isfile returns True) but failed to remove it
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: should raise OperationFailed exception
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        mock_os.path.isfile.return_value = True
        mock_os.remove.side_effect = Exception('dummy_error')
        self.assertRaises(exception.OperationFailed, _unpersist_interface,
                          device)
        mock_os.path.isfile.assert_called_once_with(ifcfg_file_path)
        mock_os.remove.assert_called_once_with(ifcfg_file_path)
        mock_wok_log.error.assert_called_with('Failed to remove file %s. '
                                              'Error: dummy_error'
                                              % ifcfg_file_path)


class WriteIfcfgParamsUnitTests(unittest.TestCase):
    """
    unit tests for _write_ifcfg_params() method using  mock module
    """
    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices.augeas', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_wirte_success(self, mock_wok_log, mock_augeas,
                           mock_get_configured_devices):
        """
        unit test to validate _write_ifcfg_params() method success scenario
        (ie., augeas will not throw any exception)
        mock_wok_log: mock of wok_log in model.nwdevices
        mock_augeas: mock of augeas module imported in model.nwdevices
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        expected behaviour: on success, _write_ifcfg_params() doesn't
                            return anything
        """
        device = '0.0.0101'
        device_name = 'enccw' + device
        ifcfg_file_pattern = ifcfg_path.replace('<deviceid>', device) + '/'
        mock_get_configured_devices.return_value = \
            {device_name: {'name': device_name, 'device_ids': ['dummy_ids']}}
        # returning attributes which are used by _write_ifcfg_params()

        _write_ifcfg_params(device)
        parser_mock = mock_augeas.Augeas('/')
        calls = [(ifcfg_file_pattern+'DEVICE', device_name,),
                 (ifcfg_file_pattern+'ONBOOT', 'yes',),
                 (ifcfg_file_pattern+'NETTYPE', 'qeth',),
                 (ifcfg_file_pattern+'SUBCHANNELS', 'dummy_ids',)]
        for i in range(0, 3):
            x, y = parser_mock.set.call_args_list[i]
            assert x == calls[i]
        assert parser_mock.set.call_count == 4
        parser_mock.load.assert_called_once_with()
        parser_mock.save.assert_called_once_with()
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices.augeas', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_wirte_exception(self, mock_wok_log, mock_augeas,
                             mock_get_configured_devices):
        """
        unit test to validate _write_ifcfg_params() method when augeas
        raises exception
        mock_wok_log: mock of wok_log in model.nwdevices
        mock_augeas: mock of augeas module imported in model.nwdevices
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        expected behaviour: _write_ifcfg_params() should raise
                            OperationFailed exception
        """
        device = '0.0.0101'
        device_name = 'enccw' + device
        mock_get_configured_devices.return_value = \
            {device_name: {'name': device_name, 'device_ids': ['dummy_ids']}}
        # returning attributes which are used by _write_ifcfg_params()
        parser_mock = mock_augeas.Augeas('/')
        parser_mock.load.side_effect = Exception('dummy_error')

        self.assertRaises(exception.OperationFailed,
                          _write_ifcfg_params, device)
        parser_mock.load.assert_called_once_with()
        self.assertFalse(parser_mock.set.called, msg='Unexpected call to '
                                                     'parser_mock.set()')
        self.assertFalse(parser_mock.save.called, msg='Unexpected call to '
                                                      'parser_mock.save()')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        mock_wok_log.error.assert_called_once_with('Failedd to write device '
                                                   'attributes to ifcfg file'
                                                   ' using augeas tool. '
                                                   'Error: dummy_error')

    @mock.patch('model.nwdevices._get_configured_devices', autospec=True)
    @mock.patch('model.nwdevices.augeas', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_wirte_keyerror(self, mock_wok_log, mock_augeas,
                            mock_get_configured_devices):
        """
        unit test to validate _write_ifcfg_params() method when key error
        is raised with dictionary mapping with _get_configured_devices
        mock_wok_log: mock of wok_log in model.nwdevices
        mock_augeas: mock of augeas module imported in model.nwdevices
        mock_get_configured_devices: mock of _get_configured_devices()
                                     method in model.nwdevices
        expected behaviour: _write_ifcfg_params() should raise
                            KeyError exception
        """
        device = '0.0.0101'
        parser_mock = mock_augeas.Augeas('/')
        mock_get_configured_devices.return_value = {'dummy': 'dict'}

        self.assertRaises(KeyError, _write_ifcfg_params, device)
        self.assertFalse(parser_mock.load.called, msg='Unexpected call to '
                                                      'parser_mock.load()')
        self.assertFalse(parser_mock.set.called, msg='Unexpected call to '
                                                     'parser_mock.set()')
        self.assertFalse(parser_mock.save.called, msg='Unexpected call to '
                                                      'parser_mock.save()')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')


class IsInterfaceOnlineUnitTests(unittest.TestCase):
    """
    unit tests for _is_interface_online() method using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_is_online_success(self, mock_os, mock_wok_log):
        """
        unit test to validate _is_interface_online() method success
        scenario(ie., device is online and no exception raised
        while opening and reading file)
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: method should return True
        """
        device = 'dummy_device'
        online_file_path = '/sys/bus/ccwgroup/devices/' + device + '/online'
        mock_os.path.isfile.return_value = True
        open_mock = mock.mock_open(read_data='1')
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            actual_out = _is_interface_online(device)
            mock_os.path.isfile.assert_called_once_with(online_file_path)
            self.assertTrue(actual_out)
            open_mock.assert_called_with(online_file_path)
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_is_online_device_offline(self, mock_os, mock_wok_log):
        """
        unit test to validate _is_interface_online() method when
        device is offline (no exception raised while opening and
        reading /sys/bus/../online file)
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: method should return False
        """
        device = 'dummy_device'
        online_file_path = '/sys/bus/ccwgroup/devices/' + device + '/online'
        mock_os.path.isfile.return_value = True
        open_mock = mock.mock_open(read_data='0')
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            actual_out = _is_interface_online(device)
            mock_os.path.isfile.assert_called_once_with(online_file_path)
            open_mock.assert_called_with(online_file_path)
            self.assertFalse(actual_out)
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_is_online_nofile(self, mock_os, mock_wok_log):
        """
        unit test to validate _is_interface_online() method with
        device not having the /sys/bus/../online file
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: method should return False
        """
        device = 'dummy_device'
        online_file_path = '/sys/bus/ccwgroup/devices/' + device + '/online'
        mock_os.path.isfile.return_value = False
        open_mock = mock.mock_open(read_data='1')
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            actual_out = _is_interface_online(device)
            mock_os.path.isfile.assert_called_once_with(online_file_path)
            self.assertFalse(open_mock.called,
                             msg='Unexpected call to open_mock')
            self.assertFalse(actual_out)
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_is_online_exception(self, mock_os, mock_wok_log):
        """
        unit test to validate _is_interface_online() method with
        exception when trying to open/read /sys/bus/../online file
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: method should return False
        """
        device = 'dummy_device'
        online_file_path = '/sys/bus/ccwgroup/devices/' + device + '/online'
        mock_os.path.isfile.return_value = True
        open_mock = mock.mock_open(read_data='1')
        open_mock.side_effect = Exception('dummy_error')
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            actual_out = _is_interface_online(device)
            mock_os.path.isfile.assert_called_once_with(online_file_path)
            open_mock.assert_called_once_with(online_file_path)
            self.assertFalse(actual_out)
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')


class CreateIfcfgFileUnitTests(unittest.TestCase):
    """
    unit tests for _create_ifcfg_file() methon using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_create_success(self, mock_os, mock_wok_log):
        """
        unit test to validate _create_ifcfg_file() method success scenario
        (ie, no exception in creating or changing permissions of file)
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: on success, method doesn't return anything
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        command = 'chmod 644 ' + ifcfg_file_path
        open_mock = mock.mock_open()
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            _create_ifcfg_file(device)
            open_mock.assert_called_once_with(ifcfg_file_path, 'w+')
            mock_os.system.assert_called_once_with(command)
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_create_openexception(self, mock_os, mock_wok_log):
        """
        unit test to validate _create_ifcfg_file() method when
        open() raises an exception
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: should raise OperationFailed exception
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        open_mock = mock.mock_open()
        open_mock.side_effect = Exception('dummy_error')
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            self.assertRaises(exception.OperationFailed,
                              _create_ifcfg_file, device)
            open_mock.assert_called_once_with(ifcfg_file_path, 'w+')
            self.assertFalse(mock_os.system.called, msg='Unexpected '
                             'call to mock_os.system()')
            mock_wok_log.error.assert_called_once_with(
                'failed to create file %s for network device'
                ' %s. Error: dummy_error' % (ifcfg_file_path, device))
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.os', autospec=True)
    def test_create_os_systemexception(self, mock_os, mock_wok_log):
        """
        unit test to validate _create_ifcfg_file() method when
        os.system() raises an exception
        mock_os: mock of os module imported in model.nwdevices
        mock_wok_log: mock of wok_log in model.nwdevices
        expected behaviour: should raise OperationFailed exception
        """
        device = 'dummy_device'
        ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device)
        command = 'chmod 644 ' + ifcfg_file_path
        mock_os.system.side_effect = Exception('dummy_error')
        open_mock = mock.mock_open()
        with mock.patch('model.nwdevices.open', open_mock, create=True):
            self.assertRaises(exception.OperationFailed,
                              _create_ifcfg_file, device)
            open_mock.assert_called_once_with(ifcfg_file_path, 'w+')
            mock_os.system.assert_called_once_with(command)
            mock_wok_log.error.assert_called_once_with(
                'failed to create file %s for network device'
                ' %s. Error: dummy_error' % (ifcfg_file_path, device))
            self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                            'mock_wok_log.info(). Not called')


class ConfigureInterfaceUnitTests(unittest.TestCase):
    """
    unit tests for _configure_interface() method using mock module
    """
    @mock.patch('model.nwdevices.RollbackContext', autospec=True)
    @mock.patch('model.nwdevices._persist_interface', autospec=True)
    @mock.patch('model.nwdevices._bring_online', autospec=True)
    @mock.patch('model.nwdevices._create_ifcfg_file', autospec=True)
    @mock.patch('model.nwdevices._is_interface_online', autospec=True)
    def test_configure_interface_success(self, mock_is_interface_online,
                                         mock_create_ifcfg_file,
                                         mock_bring_online,
                                         mock_persist_interface,
                                         mock_rollbackcontext):
        """
        unit test to validate _configure_interface() with success scenario
        mock_persist_interface: mock of _persist_interface()
                                of model.nwdevices
        mock_create_ifcfg_file: mock of _create_ifcfg_file()
                                of model.nwdevices
        mock_bring_online: mock of _bring_online() of model.nwdevices
        mock_is_interface_online: mock of _is_interface_online()
                                  of model.nwdevices
        mock_rollbackcontext: mock of wok.rollbackcontext imported as
                               RollbackContext in model.nwdevices
        """
        interface = 'test_interface'

        def cb(msg, status=None):
            pass

        mock_is_interface_online.return_value = False
        _configure_interface(cb, interface)
        mock_is_interface_online.assert_called_once_with(interface)
        mock_bring_online.assert_called_once_with(interface)
        mock_create_ifcfg_file.assert_called_once_with(interface)
        mock_persist_interface.assert_called_once_with(interface)

    @mock.patch('model.nwdevices.RollbackContext', autospec=True)
    @mock.patch('model.nwdevices._persist_interface', autospec=True)
    @mock.patch('model.nwdevices._bring_online', autospec=True)
    @mock.patch('model.nwdevices._create_ifcfg_file', autospec=True)
    @mock.patch('model.nwdevices._is_interface_online', autospec=True)
    def test_configure_interface_failure(self, mock_is_interface_online,
                                         mock_create_ifcfg_file,
                                         mock_bring_online,
                                         mock_persist_interface,
                                         mock_rollbackcontext):
        """
        unit test to validate _configure_interface() with failure scenario
        mock_persist_interface: mock of _persist_interface()
                                of model.nwdevices
        mock_create_ifcfg_file: mock of _create_ifcfg_file()
                                of model.nwdevices
        mock_bring_online: mock of _bring_online() of model.nwdevices
        mock_is_interface_online: mock of _is_interface_online()
                                  of model.nwdevices
        mock_rollbackcontext: mock of wok.rollbackcontext imported as
                        RollbackContext in model.nwdevices
        mock_bring_offline: mock of _bring_offline() of model.nwdevices
        """
        interface = 'test_interface'

        def cb(msg, status=None):
            pass

        mock_persist_interface.side_effect = Exception('dummy_error')
        mock_is_interface_online.return_value = False
        _configure_interface(cb, interface)
        mock_is_interface_online.assert_called_once_with(interface)
        mock_create_ifcfg_file.assert_called_once_with(interface)
        mock_bring_online.assert_called_once_with(interface)
        mock_persist_interface.assert_called_once_with(interface)


class UnconfigureInterfaceUnitTests(unittest.TestCase):
    """
    unit tests to validate _unconfigure_interface() method using mock module
    """
    @mock.patch('model.nwdevices._is_interface_online', autospec=True)
    @mock.patch('model.nwdevices.RollbackContext', autospec=True)
    @mock.patch('model.nwdevices._bring_offline', autospec=True)
    @mock.patch('model.nwdevices._unpersist_interface', autospec=True)
    def test_unconfigure_interface_success(self, mock_unpersist_interface,
                                           mock_bring_offline,
                                           mock_rollbackcontext,
                                           mock_is_interface_online):
        """
        unit test to validate _unconfigure_interface() with success scenario
        mock_unpersist_interface: mock of _unpersist_interface()
                                  of model.nwdevices
        mock_bring_offline: mock of _bring_offline() of model.nwdevices
        mock_is_interface_online: mock of _is_interface_online()
                                  of model.nwdevices
        mock_rollbackcontext: mock of wok.rollbackcontext imported as
                        RollbackContext in model.nwdevices
        """
        interface = 'test_interface'

        def cb(msg, status=None):
            pass

        mock_is_interface_online.return_value = True
        _unconfigure_interface(cb, interface)
        mock_is_interface_online.assert_called_once_with(interface)
        mock_bring_offline.assert_called_once_with(interface)
        mock_unpersist_interface.assert_called_once_with(interface)

    @mock.patch('model.nwdevices._unpersist_interface', autospec=True)
    @mock.patch('model.nwdevices.RollbackContext', autospec=True)
    @mock.patch('model.nwdevices._is_interface_online', autospec=True)
    @mock.patch('model.nwdevices._bring_offline', autospec=True)
    def test_unconfigure_interface_failure(self, mock_bring_offline,
                                           mock_is_interface_online,
                                           mock_rollbackcontext,
                                           mock_unpersist_interface):
        """
        unit test to validate _unconfigure_interface() with failure scenario
        mock_unpersist_interface: mock of _unpersist_interface()
                                  of model.nwdevices
        mock_bring_offline: mock of _bring_offline() of model.nwdevices
        mock_is_interface_online: mock of _is_interface_online()
                                  of model.nwdevices
        mock_rollbackcontext: mock of wok.rollbackcontext imported as
                        RollbackContext in model.nwdevices
        """
        interface = 'test_interface'

        def cb(msg, status=None):
            pass

        mock_unpersist_interface.side_effect = Exception('dummy_error')
        mock_is_interface_online.return_value = True
        _unconfigure_interface(cb, interface)
        mock_bring_offline.assert_called_once_with(interface)
        mock_bring_offline.assert_called_once_with(interface)
        mock_unpersist_interface.assert_called_once_with(interface)


class GetConfiguredDevicesUnitTests(unittest.TestCase):
    """
    unit tests for _get_configured_devices() method using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    @mock.patch('model.nwdevices.utils', autospec=True)
    def test_command_fails(self, mock_utils, mock_run_command, mock_wok_log):
        """
        unit test to validate _get_configured_devices() with run_command()
        returning non zero return code
        mock_run_command: mock of wok.utils.run_command() imported in
                          model.nwdevices
        mock_utils: mock of model_utils imported as utils in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        _get_configured_devices() should raise exception
        """
        cmd = ['znetconf', '-c']
        mock_run_command.return_value = ['', 'dummy_error', 1]
        self.assertRaises(exception.OperationFailed, _get_configured_devices)
        mock_run_command.assert_called_once_with(cmd)
        self.assertFalse(mock_utils.get_rows_info.called, msg='Unexpected '
                         'call to mock_utils.get_rows_info()')
        mock_wok_log.error.assert_called_once_with('Failed to run \"znetconf'
                                                   ' -c\" command. Error: '
                                                   'dummy_error')

    @mock.patch('model.nwdevices._format_znetconf', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    @mock.patch('model.nwdevices.utils', autospec=True)
    def test_success_withoutkey(self, mock_utils, mock_run_command,
                                mock_wok_log, mock_format_znetconf):
        """
        unit test to validate _get_configured_devices() success scenario
        without passing key
        mock_run_command: mock of wok.utils.run_command() imported in
                          model.nwdevices
        mock_utils: mock of model_utils imported as utils in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_format_znetconf: mock of _format_znetconf() method in
                              model.nwdevices

        _get_configured_devices() should return output returned
        from util.get_rows_info()
        """
        cmd = ['znetconf', '-c']
        mock_run_command.return_value = ['dummy_output', '', 0]
        mock_utils.get_rows_info.return_value = 'dummy_out'
        configured_devices = _get_configured_devices()
        mock_run_command.assert_called_once_with(cmd)
        mock_utils.get_rows_info.assert_called_once_with(
            'dummy_output',
            hdr_pattern=CONF_HDR_PATTERN,
            val_pattern=CONF_DEVICE_PATTERN,
            format_data=mock_format_znetconf,
            hdr_index=0, val_start_index=2)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        self.assertEqual(configured_devices, 'dummy_out')

    @mock.patch('model.nwdevices._format_znetconf', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    @mock.patch('model.nwdevices.utils', autospec=True)
    def test_success_withkey(self, mock_utils, mock_run_command,
                             mock_wok_log, mock_format_znetconf):
        """
        unit test to validate _get_configured_devices() success
        scenario with key
        mock_run_command: mock of wok.utils.run_command() imported in
                          model.nwdevices
        mock_utils: mock of model_utils imported as utils in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_format_znetconf: mock of _format_znetconf() method in
                              model.nwdevices

        _get_configured_devices() should return output returned
        from util.get_rows_info()
        """
        cmd = ['znetconf', '-c']
        key = 'dummy_key'
        mock_run_command.return_value = ['dummy_output', '', 0]
        mock_utils.get_rows_info.return_value = 'dummy_out'
        configured_devices = _get_configured_devices(key)
        mock_run_command.assert_called_once_with(cmd)
        mock_utils.get_rows_info.assert_called_once_with(
            'dummy_output',
            hdr_pattern=CONF_HDR_PATTERN,
            unique_col=key,
            val_pattern=CONF_DEVICE_PATTERN,
            format_data=mock_format_znetconf,
            hdr_index=0, val_start_index=2)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        self.assertEqual(configured_devices, 'dummy_out')


class GetUnConfiguredDevicesUnitTests(unittest.TestCase):
    """
    unit tests for _get_unconfigured_devices() method using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    @mock.patch('model.nwdevices.utils', autospec=True)
    def test_command_fails(self, mock_utils, mock_run_command, mock_wok_log):
        """
        unit test to validate _get_unconfigured_devices() with run_command()
        returning non zero return code
        mock_run_command: mock of wok.utils.run_command() imported in
                          model.nwdevices
        mock_utils: mock of model_utils imported as utils in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        _get_unconfigured_devices() should raise exception
        """
        cmd = ['znetconf', '-u']
        mock_run_command.return_value = ['', 'dummy_error', 1]
        self.assertRaises(exception.OperationFailed, _get_unconfigured_devices)
        mock_run_command.assert_called_once_with(cmd)
        self.assertFalse(mock_utils.get_rows_info.called, msg='Unexpected '
                         'call to mock_utils.get_rows_info()')
        mock_wok_log.error.assert_called_once_with('Failed to run \"znetconf '
                                                   '-u\" command. Error: '
                                                   'dummy_error')

    @mock.patch('model.nwdevices._format_znetconf', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    @mock.patch('model.nwdevices.utils', autospec=True)
    def test_success_withoutkey(self, mock_utils, mock_run_command,
                                mock_wok_log, mock_format_znetconf):
        """
        unit test to validate _get_unconfigured_devices() success scenario
        without passing key
        mock_run_command: mock of wok.utils.run_command() imported in
                          model.nwdevices
        mock_utils: mock of model_utils imported as utils in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_format_znetconf: mock of _format_znetconf() method in
                              model.nwdevices

        _get_unconfigured_devices() should return output returned
        from util.get_rows_info()
        """
        cmd = ['znetconf', '-u']
        mock_run_command.return_value = ['dummy_output', '', 0]
        mock_utils.get_rows_info.return_value = 'dummy_out'
        unconfigured_devices = _get_unconfigured_devices()
        mock_run_command.assert_called_once_with(cmd)
        mock_utils.get_rows_info.assert_called_once_with(
            'dummy_output',
            hdr_pattern=UNCONF_HDR_PATTERN,
            val_pattern=UNCONF_DEVICE_PATTERN,
            format_data=mock_format_znetconf,
            hdr_index=1, val_start_index=3)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        self.assertEqual(unconfigured_devices, 'dummy_out')

    @mock.patch('model.nwdevices._format_znetconf', autospec=True)
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    @mock.patch('model.nwdevices.run_command', autospec=True)
    @mock.patch('model.nwdevices.utils', autospec=True)
    def test_success_withkey(self, mock_utils, mock_run_command,
                             mock_wok_log, mock_format_znetconf):
        """
        unit test to validate _get_unconfigured_devices() success
        scenario with key
        mock_run_command: mock of wok.utils.run_command() imported in
                          model.nwdevices
        mock_utils: mock of model_utils imported as utils in model.nwdevices
        mock_wok_log: mock of wok_log of model.nwdevices
        mock_format_znetconf: mock of _format_znetconf() method in
                              model.nwdevices

        _get_unconfigured_devices() should return output returned
        from util.get_rows_info()
        """
        cmd = ['znetconf', '-u']
        key = 'dummy_key'
        mock_run_command.return_value = ['dummy_output', '', 0]
        mock_utils.get_rows_info.return_value = 'dummy_out'
        unconfigured_devices = _get_unconfigured_devices(key)
        mock_run_command.assert_called_once_with(cmd)
        mock_utils.get_rows_info.assert_called_once_with(
            'dummy_output',
            hdr_pattern=UNCONF_HDR_PATTERN,
            unique_col=key,
            val_pattern=UNCONF_DEVICE_PATTERN,
            format_data=mock_format_znetconf,
            hdr_index=1, val_start_index=3)
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
        self.assertEqual(unconfigured_devices, 'dummy_out')


class FormatZnetconfUnitTests(unittest.TestCase):
    """
    unit tests for _format_znetconf() method using mock module
    """
    def test_format_znetconf_noneinput(self):
        """
        unit test to validate _format_znetconf() with None input
        _format_znetconf() should return None
        """
        device = None
        formated_devices = _format_znetconf(device)
        self.assertEqual(formated_devices, None)

    def test_format_znetconf_emptydict_in(self):
        """
        unit test to validate _format_znetconf() with None input
        _format_znetconf() should return empty dictionary
        """
        device = {}
        formated_devices = _format_znetconf(device)
        self.assertEqual(formated_devices, {})

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_format_znetconf_keyerror(self, mock_wok_log):
        """
        unit test to validate _format_znetconf() when input dictionary
        doesn't have required keys
        mock_wok_log: mock of wok_log of model.nwdevices
        _format_znetconf() should raise KeyError exception
        """
        device = {ZNETCONF_DEV_NAME: 'dummy'
                  'inavlid_key' 'invalid'}
        log_msg = 'Issue while formatting znetconf dictionary output'
        self.assertRaises(KeyError, _format_znetconf, device)
        mock_wok_log.error.assert_called_with(log_msg)

    def test_format_with_state_name(self):
        """
        unit test to validate _format_znetconf() having all keys
        should return formatted output
        """
        device = {ZNETCONF_DEV_IDS: "1,2,3",
                  ZNETCONF_TYPE: "dummy_type",
                  ZNETCONF_CARDTYPE: "dummy_card",
                  ZNETCONF_CHPID: "dummy_chipid",
                  ZNETCONF_DRV: "dummy_driver",
                  ZNETCONF_DEV_NAME: "dummy_name",
                  ZNETCONF_STATE: "dummy_state"}
        expected_out = {'name': 'dummy_name',
                        'device_ids': ['1', '2', '3'],
                        'card_type': 'dummy_card',
                        'chpid': 'dummy_chipid',
                        'driver': 'dummy_driver',
                        'type': 'dummy_type',
                        'state': 'dummy_state'}

        actual_out = _format_znetconf(device)
        self.assertEqual(actual_out, expected_out)

    def test_format_without_state_name(self):
        """
        unit test to validate _format_znetconf() having all
        keys except ZNETCONF_DEV_NAME and ZNETCONF_STATE
        should return formatted output with 'name' as first device_id
        in ZNETCONF_DEV_IDS and 'state' should be 'Unconfigured'
        """
        device = {ZNETCONF_DEV_IDS: "1,2,3",
                  ZNETCONF_TYPE: "dummy_type",
                  ZNETCONF_CARDTYPE: "dummy_card",
                  ZNETCONF_CHPID: "dummy_chipid",
                  ZNETCONF_DRV: "dummy_driver"}
        expected_out = {'name': '1',
                        'device_ids': ['1', '2', '3'],
                        'card_type': 'dummy_card',
                        'chpid': 'dummy_chipid',
                        'driver': 'dummy_driver',
                        'type': 'dummy_type',
                        'state': 'Unconfigured'}

        actual_out = _format_znetconf(device)
        self.assertEqual(actual_out, expected_out)


class ValidateDeviceUnitTests(unittest.TestCase):
    """
    unit tests for _validate_device() method using mock module
    """
    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_validate_empty_input(self, mock_wok_log):
        """
        unit test to validate _validate_device() method with empty string
        mock_wok_log: mock of wok_log of model.nwdevices
        _validate_device() should raise InvalidParameter exception
        """
        log_msg = "interface id is empty. interface: "
        self.assertRaises(exception.InvalidParameter, _validate_device, '')
        mock_wok_log.error.assert_called_once_with(log_msg)

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_validate_invalid_device(self, mock_wok_log):
        """
        unit test to validate _validate_device() method with invalid device id
        mock_wok_log: mock of wok_log of model.nwdevices
        _validate_device() should raise InvalidParameter exception
        """
        device = 'invalid'
        log_msg = "Invalid interface id. interface: %s" % device
        self.assertRaises(exception.InvalidParameter, _validate_device, device)
        mock_wok_log.error.assert_called_once_with(log_msg)

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_validate_with_enccw(self, mock_wok_log):
        """
        unit test to validate _validate_device() method with valid device id
        with ENCCW in it(cofigured device)
        mock_wok_log: mock of wok_log of model.nwdevices
        on success _validate_device() doesn't return anything
        """
        _validate_device('enccw0.0.1234')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.nwdevices.wok_log', autospec=True)
    def test_validate_without_enccw(self, mock_wok_log):
        """
        unit test to validate _validate_device() method with valid device id
        without having ENCCW in it(unconfigured device)
        mock_wok_log: mock of wok_log of model.nwdevices
        on success _validate_device() doesn't return anything
        """
        _validate_device('0.0.1234')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')
