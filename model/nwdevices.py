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

import augeas
import os
import re

import model_utils as utils
from wok.exception import InvalidParameter, OperationFailed
from wok.model.tasks import TaskModel
from wok.rollbackcontext import RollbackContext
from wok.utils import add_task, run_command, wok_log


ZNETCONF_CMD = "znetconf"
ZNETCONF_DEV_IDS = "Device IDs"
ZNETCONF_TYPE = "Type"
ZNETCONF_CARDTYPE = "Card Type"
ZNETCONF_CHPID = "CHPID"
ZNETCONF_DRV = "Drv"
ZNETCONF_DEV_NAME = "Name"
ZNETCONF_STATE = "State"
UNIQUE_COL_NAME = "name"
DEVICE = 'DEVICE'
ONBOOT = 'ONBOOT'
SUBCHANNELS = 'SUBCHANNELS'
NETTYPE = 'NETTYPE'
ENCCW = 'enccw'

ifcfg_path = 'etc/sysconfig/network-scripts/ifcfg-enccw<deviceid>'

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


class NetworkDevicesModel(object):
    def __init__(self, **kargs):
        pass

    def get_list(self, _configured=None):
        """
        :param _configured: True will list only the network devices
        which are configured. znetconf -c will be used
        False will list only network devices which are not configured yet.
        znetconf -u will be used
        If not given then it will fetch both the list of devices.
        :return: network OSA device info list.
        """
        wok_log.info('Fetching network devices. _configured '
                     '= %s' % _configured)
        if _configured is None:
            devices = _get_configured_devices()
            devices.extend(_get_unconfigured_devices())
        elif _configured in ['True', 'true']:
            devices = _get_configured_devices()
        elif _configured in ['False', 'false']:
            devices = _get_unconfigured_devices()
        else:
            wok_log.error("Invalid _configured given. _configured: %s"
                          % _configured)
            raise InvalidParameter("GS390XINVTYPE",
                                   {'supported_type': 'True/False'})
        wok_log.info('Successfully retrieved network devices')
        return devices


class NetworkDeviceModel(object):
    def __init__(self, **kargs):
        self.objstore = kargs.get('objstore')
        self.task = TaskModel(**kargs)

    def lookup(self, name):
        """
        Gets list of all configured device info(dictionary) devices
        with name of device as key.
        If the list has the device lookup is looking for then returns
        the device info.
        Otherwise gets list of all un-configured device info devices
        with name of device as key.
        If the list has the device lookup is looking for then returns
        the device info.
        Otherwise raises InvalidParameter exception.
        :param name: name of device to lookup.
        :return: OSA device info if device found otherwise InvalidParameter
        """
        wok_log.info('Fetching attributes of network devices %s' % name)
        _validate_device(name)
        configured_devices = _get_configured_devices(key=UNIQUE_COL_NAME)
        device = configured_devices.get(name, None)
        if not device:
            unconfigured_devices = _get_unconfigured_devices(
                key=UNIQUE_COL_NAME)
            device = unconfigured_devices.get(name, None)
        if not device:
            wok_log.error('Given device is not of type OSA. Device: %s', name)
            raise InvalidParameter("GS390XINVINPUT",
                                   {'reason': 'Given device is not of type '
                                              'OSA. Device: %s' % name})
        wok_log.info('Attributes of network devices %s: %s' % (name, device))
        return device

    def configure(self, interface):
        """
        method to configure network device - bring the network
        device online and persist it
        :param interface: name of the network interface
         :return: returns task json
        """
        wok_log.info('Configuring network device %s' % interface)
        device = str(interface).strip()
        if ENCCW in device:
            # filtering out device id from interface
            device = device.replace(ENCCW, '')
        taskid = add_task('/plugins/gingers390x/nwdevices/%s/configure'
                          % interface, _configure_interface,
                          self.objstore, device)
        return self.task.lookup(taskid)

    def unconfigure(self, interface):
        """
        method to un-configure network device - remove or bring the network
        device offline and unpersist it
        :param interface: name of the network interface
        :return: returns task json
        """
        wok_log.info('Un-configuring network device %s' % interface)
        device = str(interface).strip()
        if ENCCW in device:
            # filtering out device id from interface
            device = device.replace(ENCCW, '')
        taskid = add_task('/plugins/gingers390x/nwdevices/%s/unconfigure'
                          % interface, _unconfigure_interface,
                          self.objstore, device)
        return self.task.lookup(taskid)


def _get_configured_devices(key=None):
    """
    :param key: key for which value is unique
    :return:Returns list of all the configured device info if key is None
    Else returns dictionary of configured OSA device info with key as value
    of key passed
    """
    wok_log.info('Retrieving configured devices using znetconf -c')
    cmd = [ZNETCONF_CMD, '-c']
    output, err, rc = run_command(cmd)
    if rc:
        err = err.strip().replace('znetconf:', '').strip()
        wok_log.error('Failed to run \"znetconf -c\" command. Error: %s' % err)
        raise OperationFailed("GS390XCMD0001E",
                              {'command': cmd,
                               'rc': rc, 'reason': err})

    device_pattern = r'(\d\.\d\.[0-9a-fA-F]{4},' \
                     r'\d\.\d\.[0-9a-fA-F]{4},' \
                     r'\d\.\d\.[0-9a-fA-F]{4})\s+' \
                     r'(\w+\/\w+)\s+' \
                     r'(\w+)\s+' \
                     r'([0-9a-fA-F]{2})\s+' \
                     r'(qeth)\s+' \
                     r'(\w+\d\.\d\.[0-9a-fA-F]{4})\s+' \
                     r'(\w+)\s{0,}$'

    wok_log.info('parsing znetconf -c output')
    if key:
        configured_devices = utils.get_rows_info(
            cmd_output=output,
            hdr_pattern=CONF_HDR_PATTERN,
            unique_col=key,
            val_pattern=device_pattern,
            format_data=_format_znetconf,
            hdr_index=0, val_start_index=2)
    else:
        configured_devices = utils.get_rows_info(
            cmd_output=output,
            hdr_pattern=CONF_HDR_PATTERN,
            val_pattern=device_pattern,
            format_data=_format_znetconf,
            hdr_index=0, val_start_index=2)
    wok_log.info('successfully retrieved and parsed configured devices')
    return configured_devices


def _get_unconfigured_devices(key=None):
    """
    :param key: key for which value is unique
    :return:Returns list of all the un-configured device info if key is None
    Else returns dictionary of un-configured OSA device info with key as value
    of key passed
    """
    wok_log.info('Retrieving un-configured devices using znetconf -u')
    cmd = [ZNETCONF_CMD, '-u']
    output, err, rc = run_command(cmd)

    if rc:
        err = err.strip().replace('znetconf:', '').strip()
        wok_log.error('Failed to run \"znetconf -u\" command. Error: %s' % err)
        raise OperationFailed("GS390XCMD0001E",
                              {'command': cmd,
                               'rc': rc, 'reason': err})
    device_pattern = r'(\d\.\d\.[0-9a-fA-F]{4},' \
                     r'\d\.\d\.[0-9a-fA-F]{4},' \
                     r'\d\.\d\.[0-9a-fA-F]{4})\s+' \
                     r'(\w+\/\w+)\s+' \
                     r'(OSA\s+\(\w+\))\s+' \
                     r'([0-9a-fA-F]{2})\s+' \
                     r'(qeth)\s{0,}$'

    wok_log.info('parsing znetconf -u output')
    if key:
        unconfigured_devices = utils.get_rows_info(
            cmd_output=output,
            hdr_pattern=UNCONF_HDR_PATTERN,
            unique_col=key,
            val_pattern=device_pattern,
            format_data=_format_znetconf,
            hdr_index=1, val_start_index=3)
    else:
        unconfigured_devices = utils.get_rows_info(
            cmd_output=output,
            hdr_pattern=UNCONF_HDR_PATTERN,
            val_pattern=device_pattern,
            format_data=_format_znetconf,
            hdr_index=1,
            val_start_index=3)
    wok_log.info('successfully retrieved and parsed un-configured devices')
    return unconfigured_devices


def _format_znetconf(device):
    """
    method to reform dictionary with new keys for znetconf devices
    :param device: device dictionary with keys "
            ZNETCONF_STATE, ZNETCONF_DEV_IDS, ZNETCONF_CARDTYPE,
            ZNETCONF_CHPID, ZNETCONF_DRV, ZNETCONF_TYPE, ZNETCONF_DEV_NAME,
    :return: dictionary with new keys mapped as follows
             ZNETCONF_STATE - "state", ZNETCONF_DEV_IDS - "device_ids",
             ZNETCONF_CARDTYPE- "card_type"
             ZNETCONF_CHPID - "chpid", ZNETCONF_DRV - "driver",
             ZNETCONF_TYPE - "type", ZNETCONF_DEV_NAME - "name",
             ZNETCONF_CHPID - "chipid"
             ZNETCONF_STATE if not present then its set as Un-configured.
             As for configured device, state can be both Online and Offline
             And for un configured, state is not returned in znetconf -u
             ZNETCONF_DEV_NAME is mapped to "name" and if ZNETCONF_DEV_NAME
             is not present then "name" value is set as one of the device
             from the list of deviceIds
    """
    if device:
        try:
            device['state'] = device.pop(ZNETCONF_STATE, 'Unconfigured')
            device_ids = list(device.pop(ZNETCONF_DEV_IDS).split(','))
            device['device_ids'] = device_ids
            device['card_type'] = device.pop(ZNETCONF_CARDTYPE)
            device['chpid'] = device.pop(ZNETCONF_CHPID)
            device['driver'] = device.pop(ZNETCONF_DRV)
            device['type'] = device.pop(ZNETCONF_TYPE)
            device['name'] = device.pop(ZNETCONF_DEV_NAME, device_ids[0])
        except KeyError as e:
            wok_log.error('Issue while formatting znetconf dictionary output')
            raise e
    return device


def _configure_interface(cb, interface):
    """
    method to configure and persist network device.
    Rollback is performed if it fails to persist.

    :param interface: network device id
    :return: None
    """
    cb('')  # reset messages
    try:
        with RollbackContext() as rollback:
            if not _is_interface_online(interface):
                _bring_online(interface)
                rollback.prependDefer(_bring_offline, interface)
                _create_ifcfg_file(interface)
            _persist_interface(interface)
            rollback.commitAll()
        cb('Successfully configured network device %s' % interface, True)
    except Exception as e:
        cb(e.__str__(), False)


def _unconfigure_interface(cb, interface):
    """
    method to un-configure/remove and unpersist network device.
    Rollback is performed if it fails to unpersist.

    :param interface: network device id
    :return: None
    """
    cb('')  # reset messages
    try:
        with RollbackContext() as rollback:
            if _is_interface_online(interface):
                _bring_offline(interface)
                rollback.prependDefer(_bring_online, interface)
            _unpersist_interface(interface)
            rollback.commitAll()
        cb('Successfully un-configured network device %s' % interface, True)
    except Exception as e:
        cb(e.__str__(), False)


def _validate_device(interface):
    """
    validate the device id. Valid device Ids should have
    <single digitnumber>.<single digitnumber>.<4 digit hexadecimalnumber>
    or <4 digit hexadecimal number>
    :param interface: device id
    """
    wok_log.info('Validating network interface %s' % interface)
    pattern_with_dot = r'^\d\.\d\.[0-9a-fA-F]{4}$'
    if interface and not str(interface).isspace():
        interface = str(interface).strip()
        if ENCCW in interface:
            interface = interface.strip(ENCCW)
        out = re.search(pattern_with_dot, interface)
        if out is None:
            wok_log.error("Invalid interface id. interface: %s" % interface)
            raise InvalidParameter("GS390XINVINPUT",
                                   {'reason': 'invalid interface id: %s'
                                              % interface})
        wok_log.info('Successfully validated network interface')
    else:
        wok_log.error("interface id is empty. interface: %s" % interface)
        raise InvalidParameter("GS390XINVINPUT",
                               {'reason': 'device id is required. '
                                          'device id: %s' % interface})


def _create_ifcfg_file(interface):
    """
    method to create ifcfg-enccw<device_id> file in
    /etc/sysconfig/network-scripts/ folder and change
    persmission of that file to 644 to be in sync with
    other files in directory

    :param interface: network device id
    :return: None
    """
    wok_log.info('creating ifcfg file for %s', interface)
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', interface)
    try:
        ifcfg_file = open(ifcfg_file_path, 'w+')
        ifcfg_file.close()
        os.system('chmod 644 ' + ifcfg_file_path)
        wok_log.info('created file %s for network device %s'
                     % (ifcfg_file_path, interface))
    except Exception as e:
        wok_log.error('failed to create file %s for network device %s. '
                      'Error: %s' % (ifcfg_file_path, interface, e.__str__()))
        raise OperationFailed("GS390XIONW005E",
                              {'ifcfg_file_path': ifcfg_file_path,
                               'device': interface,
                               'error': e.__str__()})


def _bring_online(interface):
    """
    method to configure network device

    :param interface: network device id
    :return: None
    """
    wok_log.info('Configuring network device %s' % interface)
    command = [ZNETCONF_CMD, '-a', interface]
    out, err, rc = run_command(command)
    if rc:
        err = ','.join(line.strip() for line in err.splitlines())
        wok_log.error('failed to configure network device %s. '
                      'Error: %s' % (interface, err))
        raise OperationFailed('GS390XIONW001E', {'device': interface,
                                                 'error': err})
    else:
        wok_log.info("Configured network device %s "
                     "successfully" % interface)


def _bring_offline(interface):
    """
    method to remove/un-configure network device

    :param interface: network device id
    :return: None
    """
    wok_log.info('Un-configuring network device %s' % interface)
    command = [ZNETCONF_CMD, '-r', interface, '-n']
    out, err, rc = run_command(command)
    if rc:
        err = ','.join(line.strip() for line in err.splitlines())
        wok_log.error('failed to un-configure network device. '
                      'Device: %s, Error: %s' % (interface, err))
        raise OperationFailed('GS390XIONW003E', {'device': interface,
                                                 'error': err})
    wok_log.info('successfully removed network device %s' % interface)


def _persist_interface(interface):
    """
    method to persist network device in by creating
    ifcfg file in /etc/sysconfig/network-scripts/ directory
    and updating required attributes in file

    :param interface: network device id
    :return: None
    """
    wok_log.info('persisting network device %s in ifcfg file' % interface)
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', interface)
    if os.path.isfile(ifcfg_file_path):
        _write_ifcfg_params(interface)
    else:
        _create_ifcfg_file(interface)
        _write_ifcfg_params(interface)
    wok_log.info('successfully persisted network device %s '
                 'in %s file' % (interface, ifcfg_file_path))


def _unpersist_interface(interface):
    """
    method to unpersist network device by removing
    ifcfg file of corresponding network device from
    /etc/sysconfig/network-scripts/ directory

    :param interface: network device id
    :return: None
    """
    wok_log.info('un persisting network device %s' % interface)
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', interface)
    try:
        if os.path.isfile(ifcfg_file_path):
            os.remove(ifcfg_file_path)
    except Exception as e:
        wok_log.error('Failed to remove file %s. Error: %s'
                      % (ifcfg_file_path, e.__str__()))
        raise OperationFailed('GS390XIONW004E',
                              {'ifcfg_file_path': ifcfg_file_path,
                               'device': interface,
                               'error': e.__str__()})
    wok_log.info('successfully removed ifcfg file %s to unpersist '
                 'network device %s' % (ifcfg_file_path, interface))


def _write_ifcfg_params(interface):
    """
    method to write mandatory attributes to ifcfg file
    of corresponding network device using augeas module
    to persist it

    :param interface: network device id
    :return: None
    """
    wok_log.info('updating mandatory params to ifcfg file of '
                 'network device %s to persist it' % interface)
    configured_devices = _get_configured_devices(key=UNIQUE_COL_NAME)
    device_info = configured_devices[ENCCW + interface]
    sub_channels = ','.join(device_info['device_ids'])
    device_name = device_info['name']
    cfgmap = {DEVICE: device_name,
              ONBOOT: 'yes',
              SUBCHANNELS: sub_channels,
              NETTYPE: 'qeth'}
    ifcfg_file_pattern = ifcfg_path.replace('<deviceid>', interface) + '/'
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', interface)
    parser = None
    try:
        parser = augeas.Augeas('/')
        parser.load()
        for key, value in cfgmap.iteritems():
            path = ifcfg_file_pattern+key
            parser.set(path, value)
        parser.save()
    except Exception as e:
        wok_log.error('Failedd to write device attributes to ifcfg file '
                      'using augeas tool. Error: %s' % e.__str__())
        raise OperationFailed('GS390XIONW002E',
                              {'device': interface,
                               'ifcfg_file_path': ifcfg_file_path,
                               'error': e.__str__()})
    finally:
        if parser:
            del parser
    wok_log.info('successfully updated mandatory params in ifcfg '
                 'file of network device %s' % interface)


def _is_interface_online(interface):
    """
    method to check if the network device is online

    :param interface: network device id
    :return: True or False
    """
    wok_log.info('checking if the network device %s is configured' % interface)
    online_file_path = '/sys/bus/ccwgroup/devices/' + interface + '/online'
    if os.path.isfile(online_file_path):
        online_file = None
        try:
            online_file = open(online_file_path)
            value = online_file.readline()
            if value and value.strip() == '1':
                wok_log.info('network device %s is '
                             'configured' % interface)
                return True
        except:
            return False
        finally:
            if online_file:
                online_file.close()
    wok_log.info('network device %s is not configured' % interface)
    return False
