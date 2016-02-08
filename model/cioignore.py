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

from wok.exception import InvalidParameter, OperationFailed
from wok.model.tasks import TaskModel
from wok.utils import add_task, run_command, wok_log

CIO_IGNORE = "cio_ignore"
IGNORED_DEVICES = 'ignored_devices'


class CIOIgnoreModel(object):
    """
    model class for ignore list
    """

    def __init__(self, **kargs):
        self.objstore = kargs.get('objstore')
        self.task = TaskModel(**kargs)

    def lookup(self, name):
        """
        method to retrieve device IDs in ignore list
        :return: returns dictionary with key as 'ignored_devices
                and value as list of device ids(single device id
                or range of device ids)
        """
        devices = {}
        command = [CIO_IGNORE, '-l']
        out, err, rc = run_command(command)
        if rc:
            wok_log.error('failed to retrieve ignore list '
                          'using \'cio_ignore -l\'. Error: %s' % err.strip())
            raise OperationFailed('GS390XIOIG001E', {'error': err.strip()})
        devices[IGNORED_DEVICES] = _parse_ignore_output(out)
        wok_log.info('Successfully retrieved devices from ignore list')
        return devices

    def remove(self, name, devices):
        """
        Remove one or more device IDs from blacklist.
        :param devices: List of devices
        :return: task json
        """
        # Check the type of devices.
        if not (isinstance(devices, list)):
            wok_log.error('Input is not of type list. Input: %s' % devices)
            raise InvalidParameter('GS390XINVINPUT', {'reason': 'input must '
                                                                'be of type'
                                                                ' list'})

        wok_log.info('Removing devices %s from ignore list' % devices)
        taskid = add_task('/plugins/gingers390x/cioignore/remove',
                          _remove_devices, self.objstore, devices)
        return self.task.lookup(taskid)


def _remove_devices(cb, devices):
    """
    Remove one or more device IDs from blacklist.
    :param devices: List of devices IDs. It can have range of device IDs
                    Ex: ['0.0.0120', '0.0.1230-0.0.1300', '0.0.001']
                    device ID format:
                            "<CSSID>.<SSID>.<DEVNO>". Ex: "0.0.0190"
                            Devices for which CSSID and SSID are 0 can
                            alternatively be specified by using only the
                            device number, either with or without leading
                            "0x" and zeros. Ex: "190", "0x190" or "0190"
    """
    cb('')  # reset messages
    try:
        wok_log.info('Removing devices %s from ignore list' % devices)
        failed_devices = {}
        for device in devices:
            device = str(device)
            if not device.isspace():
                if '-' in device:
                    # if range, remove space if any before or after '-'
                    device = device.replace(' ', '')
                command = [CIO_IGNORE, '-r', device]
                out, err, rc = run_command(command)
                if rc:
                    wok_log.error('failed to remove device(s): %s, from'
                                  ' ignore list. Error: %s'
                                  % (device, err.strip()))
                    err = err.strip().split(':')[-1].strip()
                    failed_devices[device] = err
            else:
                failed_devices[device] = 'device ID is required'
                wok_log.error('failed to remove device since'
                              ' device id is empty')

        if failed_devices:
            wok_log.error('failed to remove devices %s from'
                          ' ignore list', failed_devices)
            raise OperationFailed('GS390XIOIG002E',
                                  {'failed_devices': failed_devices})
        wok_log.info('Successfully removed devices %s from'
                     ' ignore list' % devices)
        cb('Successfully removed devices %s from ignore'
           ' list' % devices, True)
    except Exception as e:
        cb(e.__str__(), False)


def _parse_ignore_output(cmd_out):
    """
    method to parse 'cio_ignore -l' output
    devices data will be considered from 3rd row onwards
        Example input:
            Ignored devices:
            =================
            0.0.0011
            0.0.0013-0.0.0015
            0.0.001a-0.0.0020
        Example output:
            ['0.0.0011', '0.0.0013-0.0.0015', '0.0.001a-0.0.0020']

    :param cmd_out: 'cio_ignore -l' command output
    :return: list of devices in ignore list devvice can
             be single device ID or range of device IDs
    """
    devices = []
    if cmd_out:
        rows = cmd_out.splitlines()
        for row in rows[2:]:
            devices.append(row.strip())
    return devices
