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

import augeas
import os
import re

import model_utils as utils
from wok.asynctask import AsyncTask
from wok.exception import InvalidParameter, InvalidOperation
from wok.exception import NotFoundError, OperationFailed
from wok.model.tasks import TaskModel
from wok.rollbackcontext import RollbackContext
from wok.utils import run_command, wok_log


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
TYPE = 'TYPE'
ETHERNET = 'Ethernet'
ENCCW = 'enccw'
OPTIONS = 'OPTIONS'

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

SYSFS_TRIPLET_PATH = '/sys/bus/ccwgroup/drivers/qeth/'


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
            raise NotFoundError("GS390XIONW006E", {'device': name})
        wok_log.info('Attributes of network devices %s: %s' % (name, device))
        return device

    def configure(self, interface, osa_portno):
        """
        method to configure network device - bring the network
        device online and persist it
        :param interface: name of the network interface
         :return: returns task json
        """
        wok_log.info('Configuring network device %s' % interface)
        if isinstance(interface, unicode):
            # as str() cannot be done on non ascii unicode
            # it needs encoded value
            interface = interface.encode('utf-8')
        device = str(interface).strip()
        if ENCCW in device:
            # filtering out device id from interface
            device = device.replace(ENCCW, '')
        params = {'osa_portno': osa_portno,
                  'interface': device}
        taskid = AsyncTask('/plugins/gingers390x/nwdevices/%s/configure'
                           % interface, _configure_interface, params).id
        return self.task.lookup(taskid)

    def unconfigure(self, interface):
        """
        method to un-configure network device - remove or bring the network
        device offline and unpersist it
        :param interface: name of the network interface
        :return: returns task json
        """
        wok_log.info('Un-configuring network device %s' % interface)
        if isinstance(interface, unicode):
            # as str() cannot be done on non ascii unicode
            # it needs encoded value
            interface = interface.encode('utf-8')
        device = str(interface).strip()
        if ENCCW in device:
            # filtering out device id from interface
            device = device.replace(ENCCW, '')
        taskid = AsyncTask('/plugins/gingers390x/nwdevices/%s/unconfigure'
                           % interface, _unconfigure_interface, device).id
        return self.task.lookup(taskid)

    def update(self, interface, params):
        """
        method to un-configure network device - remove or bring the network
        device offline and unpersist it
        :param interface: name of the network interface
        :return: returns task json
        """
        wok_log.info('In NetworkDeviceModel.update(%s, %s) method'
                     % (interface, params))
        if not _get_configured_devices(key=UNIQUE_COL_NAME).get(interface):
            raise InvalidOperation('GS390XIONW007E')
        _update_osaport(interface, params)
        wok_log.info('End of NetworkDeviceModel.update(%s, %s) method'
                     % (interface, params))
        return interface


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
             osa_portno: OSA port used by the OSA express network card
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
            if device['state'] == 'Unconfigured':
                # for un-configured device portno is not applicable
                device['osa_portno'] = 'n/a'
            else:
                device['osa_portno'] = _get_osaport(device_ids[0])
        except KeyError as e:
            wok_log.error('Issue while formatting znetconf dictionary output')
            raise e
    return device


def _configure_interface(cb, params):
    """
    method to configure and persist network device.
    Rollback is performed if it fails to persist.

    :param interface: network device id
    :return: None
    """
    osa_portno = params.get('osa_portno')
    interface = params.get('interface')
    cb('')  # reset messages
    try:
        with RollbackContext() as rollback:
            if not _is_interface_online(interface):
                osa_portno = _bring_online(interface, osa_portno)
                rollback.prependDefer(_bring_offline, interface)
                _create_ifcfg_file(interface)
            _persist_interface(interface, osa_portno)
            rollback.commitAll()
        cb('Successfully configured network device %s' % interface, True)
    except Exception as e:
        cb(e.message, False)


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
        cb(e.message, False)


def _validate_device(interface):
    """
    validate the device id. Valid device Ids should have
    <single digitnumber>.<single digitnumber>.<4 digit hexadecimalnumber>
    or <4 digit hexadecimal number>
    :param interface: device id
    """
    wok_log.info('Validating network interface %s' % interface)
    pattern_with_dot = r'^\d\.\d\.[0-9a-fA-F]{4}$'
    if isinstance(interface, unicode):
        interface = interface.encode('utf-8')
    if interface and not str(interface).isspace():
        interface = str(interface).strip()
        if ENCCW in interface:
            interface = interface.replace(ENCCW, '')
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
        if isinstance(ifcfg_file_path, unicode):
            # as os.system default encoding is ascii and not utf8
            ifcfg_file_path.encode('utf-8')
        os.system('chmod 644 ' + ifcfg_file_path)
        wok_log.info('created file %s for network device %s'
                     % (ifcfg_file_path, interface))
    except Exception as e:
        wok_log.error('failed to create file %s for network device %s. '
                      'Error: %s' % (ifcfg_file_path, interface, e.message))
        raise OperationFailed("GS390XIONW005E",
                              {'ifcfg_file_path': ifcfg_file_path,
                               'device': interface,
                               'error': e.message})


def _bring_online(interface, osa_portno=None):
    """
    method to configure network device

    :param interface: network device id
    :return: None
    """
    wok_log.info('Configuring network device %s with port number %s'
                 % (interface, osa_portno))
    # form command as per osa_port
    command = [ZNETCONF_CMD, '-a', interface, '-o', 'portno=%s' % osa_portno]\
        if isinstance(osa_portno, int) else [ZNETCONF_CMD, '-a', interface]
    out, err, rc = run_command(command)
    # znetconf command gives non zero rc if the osa port is not available
    # for the adapter, but configures the triplet with default port(port 0)
    if rc:
        if 'Failed to configure portno' in err:
            # if failed to configure port, port 0 is used by default
            osa_portno = '0'
        else:
            # raise exception for errors excluding port configuration
            err = ','.join(line.strip() for line in err.splitlines())
            wok_log.error('failed to configure network device %s. '
                          'Error: %s' % (interface, err))
            raise OperationFailed('GS390XIONW001E', {'device': interface,
                                                     'error': err})
    wok_log.info("Configured network device %s "
                 "successfully" % interface)
    return osa_portno


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


def _persist_interface(interface, osa_portno):
    """
    method to persist network device in by creating
    ifcfg file in /etc/sysconfig/network-scripts/ directory
    and updating required attributes in file

    :param interface: network device id
    :return: None
    """
    wok_log.info('persisting network device %s in ifcfg file' % interface)
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', interface)
    if isinstance(ifcfg_file_path, unicode):
        ifcfg_file_path = ifcfg_file_path.encode('utf-8')
    if os.path.isfile(ifcfg_file_path):
        _write_ifcfg_params(interface, osa_portno)
    else:
        _create_ifcfg_file(interface)
        _write_ifcfg_params(interface, osa_portno)
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
    if isinstance(ifcfg_file_path, unicode):
        ifcfg_file_path = ifcfg_file_path.encode('utf-8')
    try:
        if os.path.isfile(ifcfg_file_path):
            os.remove(ifcfg_file_path)
    except Exception as e:
        wok_log.error('Failed to remove file %s. Error: %s'
                      % (ifcfg_file_path, e.message))
        raise OperationFailed('GS390XIONW004E',
                              {'ifcfg_file_path': ifcfg_file_path,
                               'device': interface,
                               'error': e.message})
    wok_log.info('successfully removed ifcfg file %s to unpersist '
                 'network device %s' % (ifcfg_file_path, interface))


def _write_ifcfg_params(interface, osa_portno):
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
              NETTYPE: 'qeth',
              TYPE: ETHERNET}
    ifcfg_file_pattern = ifcfg_path.replace('<deviceid>', interface) + '/'
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', interface)
    parser = None
    try:
        parser = augeas.Augeas('/')
        parser.load()
        for key, value in cfgmap.iteritems():
            path = ifcfg_file_pattern+key
            parser.set(path, value)
        # add OPTIONS attribute with layer2 and osa port number
        optns = _form_cfg_options_attr(
            osa_portno, parser.get(ifcfg_file_pattern+OPTIONS))
        parser.set(ifcfg_file_pattern+OPTIONS, optns)
        parser.save()
    except Exception as e:
        wok_log.error('Failed to write device attributes to ifcfg file '
                      'using augeas tool. Error: %s' % e.message)
        raise OperationFailed('GS390XIONW002E',
                              {'device': interface,
                               'ifcfg_file_path': ifcfg_file_path,
                               'error': e.message})
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
    if isinstance(online_file_path, unicode):
        online_file_path = online_file_path.encode('utf-8')
    if os.path.isfile(online_file_path):
        online_file = None
        try:
            online_file = open(online_file_path)
            value = online_file.read()
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


def _get_osaport(device_id):
    """
    method to get port number of triplet configured

    Args:
        device_id: first bus id of the triplet

    Returns: osa port used by OSA Express card

    """
    device_id = device_id.strip() if ENCCW not in device_id else \
        device_id.replace(ENCCW, '').strip()
    portno_file = os.path.join(SYSFS_TRIPLET_PATH + device_id + '/portno')
    if os.path.isfile(portno_file):
        try:
            with open(portno_file, 'r') as port_file:
                return int(port_file.read().strip())
        except Exception as e:
            wok_log.error('Failed to read osa port number for devie "%s". '
                          'Error: "%s"' % (device_id, e.message))
    return 'n/a'


def _form_cfg_options_attr(portno, options):
    """
    method to form OPTIONS attribute of ifcfg file

    Example: OPTIONS="layer2=1 portno=0 buffer_count=128"

    valid OPTIONS attribute includes options like
    layer2, portno, buffercount etc
    this method focus on replacing only portno with given port
    """
    wok_log.info('In _form_cfg_options_attr(%s, %s) method'
                 % (portno, options))
    # use 0 port by default if portno is not provided
    portno = portno if isinstance(portno, int) else 0
    if options and not options.isspace():
        if re.match(r'^[\"\'][^\"\']*[\"\']$', options):
            # valid OPTIONS value will be enclosed by
            # either single or double quotes
            if re.search(r'portno=\d', options):
                return re.sub(r'portno=\d', 'portno=%s' % portno, options)
            else:
                return options.rstrip(options[-1]) \
                          + 'portno=%s' % portno + options[0]
    wok_log.info('End of _form_cfg_options_attr(%s, %s) method'
                 % (portno, options))
    return '"layer2=1 portno=%s"' % portno


def _update_osaport(interface, params):
    """
    method to configure osa port and write in configuration file
    Args:
        interface: interface name of the configured triplet
        params: params having osa_portno to update

    Returns:

    """
    wok_log.info('In _update_osaport(%s, %s) method'
                 % (interface, params))
    device_id = interface.strip() if ENCCW not in interface else \
        interface.replace(ENCCW, '').strip()  # get bus id
    osa_portno = params.get('osa_portno')
    if not isinstance(osa_portno, int):
        raise InvalidParameter('GS390XIONW009E')
    # check if the given osa port is same as configured osa port
    if osa_portno != _get_osaport(device_id):
        _configure_osa_portno(device_id, osa_portno)
    _write_osaport_to_cfgfile(device_id, osa_portno)
    wok_log.info('End of _update_osaport(%s, %s) method'
                 % (interface, params))


def _configure_osa_portno(device_id, osa_portno):
    """
    method to configure osa port for OSA Express card
    this method writes given osa port number in portno
    file of SYSFS_TRIPLET_PATH
    Args:
        device_id: first bus id of configuder triplet
        osa_portno: osa port number
    """
    wok_log.info('In _configure_osa_portno(%s, %s) method'
                 % (device_id, osa_portno))
    device_id = device_id.strip() if ENCCW not in device_id else \
        device_id.replace(ENCCW, '').strip()
    online_path = os.path.join(SYSFS_TRIPLET_PATH + device_id + '/online')
    portno_path = os.path.join(SYSFS_TRIPLET_PATH + device_id + '/portno')
    bring_online = False
    try:
        # avoid writing '0' into online file for a interface which is
        # already offline. Else it will throw write error
        if _is_interface_online(device_id):
            with open(online_path, 'w') as online_file:
                # bring interface offline
                online_file.write('0')
            wok_log.info('brought device "%s" offline' % device_id)
            bring_online = True
        try:
            with open(portno_path, 'w') as portno_file:
                # configure osa port in portno file
                portno_file.write(str(osa_portno))
            wok_log.info('configure osa port "%s" for device "%s"' %
                         (osa_portno, device_id))
        except IOError as e:
            # if its write error then corresponding port is
            # not available
            if '[Errno 22] Invalid argument' in e.__str__():
                wok_log.error(
                    'Port number "%s" may not be availble since write '
                    'on file "%s" failed.' % (osa_portno, portno_path))
            raise OperationFailed('GS390XIONW010E',
                                  {'interface': 'enccw' + device_id,
                                   'osa_portno': osa_portno})
        with open(online_path, 'w') as online_file:
            # bring interface online
            online_file.write('1')
        wok_log.info('brought device "%s" online' % device_id)
        bring_online = False
    except OperationFailed:
        raise
    except Exception as e:
        wok_log.error('Failed to configure osa port number for device "%s". '
                      'Error: "%s"' % (device_id, e.__str__()))
        raise OperationFailed('GS390XIONW008E',
                              {'device': 'enccw' + device_id,
                               'error': e.__str__()})
    finally:
        if bring_online:
            # rollback if the interface was brought offline
            with open(online_path, 'w') as online_file:
                online_file.write('1')
        wok_log.info('End of _configure_osa_portno(%s, %s) method'
                     % (device_id, osa_portno))


def _write_osaport_to_cfgfile(device_id, osa_portno):
    """
    write osa port number into ifcfg file for the corresponding interface
    this method creates ifcfg file with defualt params if file doesn't exist
    Args:
        device_id: first bus id of the network triplet
        osa_portno: OSA port number
    """
    wok_log.info('In _write_osaport_to_cfgfile() method. Updating osa port'
                 ' number "%s" for device "%s"' % (osa_portno, device_id))
    ifcfg_file_path = '/' + ifcfg_path.replace('<deviceid>', device_id)
    if not os.path.isfile(ifcfg_file_path):
        wok_log.info('ifcfg file is not there for interface "%s". creating'
                     ' ifcfg file with default values and osa port numer "%s'
                     % (device_id, osa_portno))
        # if the ifcfg file doesn't exist, follow persist interface to create
        # ifcfg file and write persistence params
        return _persist_interface(device_id, osa_portno)

    ifcfg_file_pattern = ifcfg_path.replace('<deviceid>', device_id) + '/'
    wok_log.info('Update osa port number "%s" in file "%s" usaing augeas'
                 % (osa_portno, ifcfg_file_path))
    try:
        parser = augeas.Augeas('/')
        parser.load()
        wok_log.info('Get current osa port number "%s" from file "%s"'
                     % (osa_portno, ifcfg_file_path))
        optns = _form_cfg_options_attr(
            osa_portno, parser.get(ifcfg_file_pattern+OPTIONS))
        parser.set(ifcfg_file_pattern+OPTIONS, optns)
        parser.save()
        wok_log.info('Updated osa port number "%s" in file "%s"'
                     % (osa_portno, ifcfg_file_path))
    except Exception as e:
        wok_log.error('Failed to write osa port number to ifcfg file '
                      'using augeas tool. Error: %s' % e.message)
        raise OperationFailed('GS390XIONW002E',
                              {'device': device_id,
                               'ifcfg_file_path': ifcfg_file_path,
                               'error': e.message})
    finally:
        if parser:
            del parser
        wok_log.info('End of _write_osaport_to_cfgfile(%s, %s) method'
                     % (device_id, osa_portno))
