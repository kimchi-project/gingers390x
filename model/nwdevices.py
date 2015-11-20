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

import re

import model_utils as utils
from wok.exception import InvalidParameter, OperationFailed
from wok.model.tasks import TaskModel
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
