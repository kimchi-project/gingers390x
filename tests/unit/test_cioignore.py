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
from model.cioignore import CIOIgnoreModel
from model.cioignore import _parse_ignore_output, _remove_devices

CIO_IGNORE = "cio_ignore"
IGNORED_DEVICES = 'ignored_devices'


class PostOperationUnitTests(unittest.TestCase):
    """
    unit tests for post operations in CIOIgnoreModel using mock module
    """
    @mock.patch('model.cioignore.wok_log', autospec=True)
    @mock.patch('model.cioignore.add_task', autospec=True)
    @mock.patch('model.cioignore.TaskModel', autospec=True)
    def test_model_remove_listin(self, mock_task_model, mock_add_task,
                                 mock_wok_log):
        """
        unit test to validate remove() action with success scenario
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.cioignore
        mock_add_task: mock of model.utils.add_task() imported
                       in model.cioignore
        mock_wok_log: mock of wok_log of model.cioignore
        """
        device = ['devce1']
        taskid = 1
        mock_add_task.return_value = taskid
        mock_task_model.lookup.return_value = "test_task"
        cio_model = CIOIgnoreModel(kargs=None)
        cio_model.remove('', device)
        self.assertTrue(mock_add_task.called,
                        msg='Expected call to mock_add_task(). Not Called')
        self.assertTrue(mock_wok_log.info.called, msg='Expected call to '
                        'mock_wok_log.info(). Not called')

    @mock.patch('model.cioignore.wok_log', autospec=True)
    @mock.patch('model.cioignore.add_task', autospec=True)
    @mock.patch('model.cioignore.TaskModel', autospec=True)
    def test_model_remove_input_notlist(self, mock_task_model, mock_add_task,
                                        mock_wok_log):
        """
        unit test to validate remove() action with input which is not list
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.cioignore
        mock_add_task: mock of model.utils.add_task() imported
                       in model.cioignore
        mock_wok_log: mock of wok_log of model.cioignore

        remove() action should raise InvalidParameter Exception
        """
        device = 'device1'
        taskid = 1
        mock_add_task.return_value = taskid
        mock_task_model.lookup.return_value = "test_task"
        cio_model = CIOIgnoreModel(kargs=None)
        self.assertRaises(exception.InvalidParameter, cio_model.remove,
                          '', device)
        self.assertFalse(mock_add_task.called,
                         msg='Unexpected call to mock_add_task()')
        mock_wok_log.error.assert_called_once_with('Input is not of type '
                                                   'list. Input: %s' % device)


class RemoveDevicesUnitTests(unittest.TestCase):
    """
    unit tests for _remove_devices() method
    """
    @mock.patch('model.cioignore.run_command', autospec=True)
    @mock.patch('model.cioignore.wok_log', autospec=True)
    def test_remove_devices_success_withoutrange(self, mock_wok_log,
                                                 mock_run_command):
        """
        unit test to validate _remove_devices() success scenario
        in which the device list doesn't include range of devices
        mock_wok_log: mock of wok_log of model.cioignore
        mock_run_command: mock of wok.utils.run_command imported
                          in model.cioignore
        """
        devices = ['device1', 'device2']
        mock_run_command.return_value = ['', '', 0]

        def cb(msg, status=None):
            pass

        _remove_devices(cb, devices)
        calls_run_command = [([CIO_IGNORE, '-r', 'device1'],),
                             ([CIO_IGNORE, '-r', 'device2'],)]
        for i in range(0, 2):
            x, y = mock_run_command.call_args_list[i]
            assert x == calls_run_command[i]
        assert mock_run_command.call_count == 2
        self.assertTrue(mock_wok_log.info.called,
                        msg='Expected call to mock_wok_log.info().'
                            ' Not called')

    @mock.patch('model.cioignore.run_command', autospec=True)
    @mock.patch('model.cioignore.wok_log', autospec=True)
    def test_remove_devices_success_withrange(self, mock_wok_log,
                                              mock_run_command):
        """
        unit test to validate _remove_devices() success scenario
        in which the device list includes range of devices
        list includes combination of integer and string ids
        mock_wok_log: mock of wok_log of model.cioignore
        mock_run_command: mock of wok.utils.run_command imported
                          in model.cioignore
        """
        devices = ['dev1', 'dev2 - dev20', 25, 'dev26']
        mock_run_command.return_value = ['', '', 0]

        def cb(msg, status=None):
            pass

        _remove_devices(cb, devices)
        calls_run_command = [([CIO_IGNORE, '-r', 'dev1'],),
                             ([CIO_IGNORE, '-r', 'dev2-dev20'],),
                             ([CIO_IGNORE, '-r', '25'],),
                             ([CIO_IGNORE, '-r', 'dev26'],)]
        for i in range(0, 2):
            x, y = mock_run_command.call_args_list[i]
            assert x == calls_run_command[i]
        assert mock_run_command.call_count == 4
        self.assertTrue(mock_wok_log.info.called,
                        msg='Expected call to mock_wok_log.info().'
                            ' Not called')

    @mock.patch('model.cioignore.run_command', autospec=True)
    @mock.patch('model.cioignore.wok_log', autospec=True)
    def test_remove_devices_some_invalid_ids(self, mock_wok_log,
                                             mock_run_command):
        """
        unit test to validate _remove_devices() when list of
        devices include invalid devices
        mock_wok_log: mock of wok_log of model.cioignore
        mock_run_command: mock of wok.utils.run_command imported
                          in model.cioignore
        _remove_devices() should remove only the valid devices from ignore
        list and should throw operation failed exception and task fails
        with list of invalid devices
        """
        devices = ['device1', 'invalid', '  ']
        mock_run_command.side_effect = [['', '', 0],
                                        ['', 'dummy_error', 1]]

        def cb(msg, status=None):
            pass

        _remove_devices(cb, devices)
        calls_run_command = [([CIO_IGNORE, '-r', 'device1'],),
                             ([CIO_IGNORE, '-r', 'invalid'],)]
        for i in range(0, 2):
            x, y = mock_run_command.call_args_list[i]
            assert x == calls_run_command[i]
        assert mock_run_command.call_count == 2
        self.assertTrue(mock_wok_log.error.called,
                        msg='Expected call to mock_wok_log.info().'
                            ' Not called')


class ParseIgnoreOutput(unittest.TestCase):
    """
    unit tests for _parse_ignore_output()
    """
    def test_parse_without_data_in_cmdout(self):
        """
        unit test to validate _parse_ignore_output() to parse
        cioignore command output which dosn't have any devices
        _parse_ignore_output() should return empty list
        """
        cmd_out = 'ignore_lis\n\n'
        actual_out = _parse_ignore_output(cmd_out)
        self._baseAssertEqual(actual_out, [])

    def test_parse_with_deviceinfo(self):
        """
        unit test to validate _parse_ignore_output() to parse
        cioignore command output has devices
        _parse_ignore_output() should return list of rows
        """
        cmd_out = 'ignore_lis\n--\ndev1\ndev6-dev9\nrow3'
        expected_out = ['dev1', 'dev6-dev9', 'row3']
        actual_out = _parse_ignore_output(cmd_out)
        self._baseAssertEqual(actual_out, expected_out)


class LookUpUnitTests(unittest.TestCase):
    """
    unit tests to validate lookup() method of CIOIgnoreModel
    """
    @mock.patch('model.cioignore.TaskModel', autospec=True)
    @mock.patch('model.cioignore.wok_log', autospec=True)
    @mock.patch('model.cioignore.run_command', autospec=True)
    @mock.patch('model.cioignore._parse_ignore_output', autospec=True)
    def test_lookup_nodevice_in_ignorelist(self, mock_parse_ignore_output,
                                           mock_run_command, mock_wok_log,
                                           mock_task_model):
        """
        unit test to validate lookuo() when there is no device in ignore list
        (ie, run_command succeeds and _parse_ignore_out returns empty list)
        mock_run_command: mock of wok.utils.run_command imported
                          in model.cioignore
        mock_wok_log: mock of wok_log of model.cioignore
        mock_parse_ignore_output: mock of _parse_ignore_output()
                                  model.cioignore
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.cioignore
        """
        command = [CIO_IGNORE, '-l']
        mock_run_command.return_value = ['dummy_out', '', 0]
        mock_parse_ignore_output.return_value = []
        expected_out = {'ignored_devices': []}
        ciomodel = CIOIgnoreModel()
        actual_out = ciomodel.lookup(None)
        self.assertEqual(actual_out, expected_out)
        mock_run_command.assert_called_once_with(command)
        mock_parse_ignore_output.assert_called_once_with('dummy_out')
        self.assertTrue(mock_wok_log.info.called,
                        msg='Expected call to mock_wok_log.info().'
                            ' Not Called')

    @mock.patch('model.cioignore.TaskModel', autospec=True)
    @mock.patch('model.cioignore.wok_log', autospec=True)
    @mock.patch('model.cioignore.run_command', autospec=True)
    @mock.patch('model.cioignore._parse_ignore_output', autospec=True)
    def test_lookup_withdevices_in_ignorelist(self, mock_parse_ignore_output,
                                              mock_run_command, mock_wok_log,
                                              mock_task_model):
        """
        unit test to validate lookuo() when devices in ignore list
        (_parse_ignore_out returns list of devices)
        mock_run_command: mock of wok.utils.run_command imported
                          in model.cioignore
        mock_wok_log: mock of wok_log of model.cioignore
        mock_parse_ignore_output: mock of _parse_ignore_output()
                                  model.cioignore
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.cioignore
        """
        command = [CIO_IGNORE, '-l']
        mock_run_command.return_value = ['dummy_out', '', 0]
        mock_parse_ignore_output.return_value = ['dev1', '2-20', 3]
        expected_out = {'ignored_devices': ['dev1', '2-20', 3]}
        ciomodel = CIOIgnoreModel()
        actual_out = ciomodel.lookup(None)
        self.assertEqual(actual_out, expected_out)
        mock_run_command.assert_called_once_with(command)
        mock_parse_ignore_output.assert_called_once_with('dummy_out')
        self.assertTrue(mock_wok_log.info.called,
                        msg='Expected call to mock_wok_log.info().'
                            ' Not Called')

    @mock.patch('model.cioignore.TaskModel', autospec=True)
    @mock.patch('model.cioignore.wok_log', autospec=True)
    @mock.patch('model.cioignore.run_command', autospec=True)
    @mock.patch('model.cioignore._parse_ignore_output', autospec=True)
    def test_lookup_command_fails(self, mock_parse_ignore_output,
                                  mock_run_command, mock_wok_log,
                                  mock_task_model):
        """
        unit test to validate lookup() when run_command() fails
        (_parse_ignore_out returns list of devices)
        mock_run_command: mock of wok.utils.run_command imported
                          in model.cioignore
        mock_wok_log: mock of wok_log of model.cioignore
        mock_parse_ignore_output: mock of _parse_ignore_output()
                                  model.cioignore
        mock_task_model: mock of wok.model.tasks imported as TaskModel
                        in model.cioignore

        lookup() should raise OperationFailed Exception
        """
        command = [CIO_IGNORE, '-l']
        mock_run_command.return_value = ['', 'dummy_error', 1]
        ciomodel = CIOIgnoreModel()
        self.assertRaises(exception.OperationFailed, ciomodel.lookup, None)
        mock_run_command.assert_called_once_with(command)
        self.assertFalse(mock_parse_ignore_output.called,
                         msg='Unexpected call to mock_parse_ignore_output()')
        mock_wok_log.error.assert_called_once_with('failed to retrieve ignore'
                                                   ' list using \'cio_ignore '
                                                   '-l\'. Error: dummy_error')
