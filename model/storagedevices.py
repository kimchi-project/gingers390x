#
# Project Ginger S390x
#
# Copyright IBM, Corp. 2015-2016
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

import binascii
import os
import re

import model_utils as utils
from wok.exception import InvalidParameter, OperationFailed
from wok.rollbackcontext import RollbackContext
from wok.utils import run_command, wok_log


DEV_TYPES = ["dasd-eckd", "zfcp"]
syspath_eckd = "/sys/bus/ccw/drivers/dasd-eckd/0.*/"
syspath_zfcp = "/sys/bus/ccw/drivers/zfcp/0.*/"
lscss = "lscss"
chccwdev = 'chccwdev'
LSCSS_DEV = "Device"
LSCSS_SUBCH = "Subchan"
LSCSS_DEVTYPE = "DevType"
LSCSS_CUTYPE = "CU Type"
LSCSS_USE = "Use"
LSCSS_PIM = "PIM"
LSCSS_PAM = "PAM"
LSCSS_POM = "POM"
LSCSS_CHPID = "CHPIDs"
HEADER_PATTERN = r'('+re.escape(LSCSS_DEV) + r')\s+' \
                 r'('+re.escape(LSCSS_SUBCH) + r')\.\s+' \
                 r'('+re.escape(LSCSS_DEVTYPE) + r')\s+' \
                 r'('+re.escape(LSCSS_CUTYPE) + r')\s+' \
                 r'('+re.escape(LSCSS_USE) + r')\s+' \
                 r'('+re.escape(LSCSS_PIM) + r')\s+' \
                 r'('+re.escape(LSCSS_PAM) + r')\s+' \
                 r'('+re.escape(LSCSS_POM) + r')\s+' \
                 r'('+re.escape(LSCSS_CHPID) + r')$'
DASD_CONF = '/etc/dasd.conf'
ZFCP_CONF = '/etc/zfcp.conf'


class StorageDevicesModel(object):
    """
    Model class for Storage Devices
    """
    def __init__(self, **kargs):
        pass

    def get_list(self, _type=None):
        """
        :param _type: supported types are dasd-eckd, zfcp.
        Based on this devices will be retrieved
        :return: device data list.
        """
        device_paths = []
        if _type is None:
            device_paths.extend(utils.get_directories(syspath_eckd))
            device_paths.extend(utils.get_directories(syspath_zfcp))
        elif _type == DEV_TYPES[0]:
            device_paths = utils.get_directories(syspath_eckd)
        elif _type == DEV_TYPES[1]:
            device_paths = utils.get_directories(syspath_zfcp)
        else:
            wok_log.error("Invalid _type given. _type: %s"
                          % _type)
            raise InvalidParameter("GS390XINVTYPE",
                                   {'supported_type': DEV_TYPES})
        if not device_paths:
            return []
        command = [lscss]
        msg = 'The command executed is "%s" ' % command
        wok_log.debug(msg)
        out, err, rc = run_command(command)
        if rc:
            err = err.strip().replace("lscss:", '').strip()
            wok_log.error(err)
            raise OperationFailed("GS390XCMD0001E",
                                  {'command': command,
                                   'rc': rc, 'reason': err})

        device_pattern = r'(\d\.\d\.[0-9a-fA-F]{4})\s+' \
                         r'(\d\.\d\.[0-9a-fA-F]{4})\s+' \
                         r'(\w+\/\w+)\s+' \
                         r'(\w+\/\w+)\s' \
                         r'(\s{3}|yes)\s+' \
                         r'([0-9a-fA-F]{2})\s+' \
                         r'([0-9a-fA-F]{2})\s+' \
                         r'([0-9a-fA-F]{2})\s+' \
                         r'(\w+\s\w+)'

        devices = utils.get_rows_info(out, HEADER_PATTERN, device_pattern,
                                      unique_col='device',
                                      format_data=_format_lscss)
        device_data_list = _list_devicesinfo(devices, device_paths)
        return device_data_list


class StorageDeviceModel(object):
    """
    Model class for Storage Device
    """
    def __init__(self, **kargs):
        pass

    def get_storagedevice(self, device):
        """
        get the device info dict for the device passed as parameter.
        Raises exception on failure of lscss execution or device is None/blank
        :param device: device id for which we need info to be returned
        :return: device info dict
        """
        device = _validate_device(device)
        if _is_dasdeckd_device(device) or _is_zfcp_device(device):
            command = [lscss, '-d', device]
            msg = 'The command is "%s" ' % command
            wok_log.debug(msg)
            out, err, rc = run_command(command)
            messge = 'The output of command "%s" is %s' % (command, out)
            wok_log.debug(messge)
            if rc:
                err = err.strip().replace("lscss:", '').strip()
                wok_log.error(err)
                raise OperationFailed("GS390XCMD0001E",
                                      {'command': command,
                                       'rc': rc, 'reason': err})
            if out.strip():
                device_info = _get_deviceinfo(out, device)
                return device_info
            wok_log.error("lscss output is either blank or None")
            raise OperationFailed("GS390XCMD0001E",
                                  {'command': command,
                                   'rc': rc, 'reason': out})
        else:
            wok_log.error("Given device id is of type dasd-eckd or zfcp. "
                          "Device: %s" % device)
            raise InvalidParameter("GS390XINVINPUT",
                                   {'reason': 'given device is not of type '
                                              'dasd-eckd or zfcp. '
                                              'Device : %s' % device})

    def lookup(self, device):
        device_info = self.get_storagedevice(device)
        return device_info

    def online(self, device):
        """
        Bring the device online.
        :param device: device id
        """
        device = _validate_device(device)
        _device_online(device)

    def offline(self, device):
        """
        Bring the device offline.
        :param device: device id
        """
        device = _validate_device(device)
        _device_offline(device)


def _format_lscss(device):
    """
    method to reform dictionary with new keys for lscss device
    :param device: device dictionary with keys "
            Device", "Subchan", "DevType",
            "CU Type", "Use", "PIM", "PAM",
            "POM", "CHPIDs"
    :return: dictionary with new keys mapped as follows
             "Device" - "device", "Subchan" - "sub_channel",
             "DevType" - "device_type"
             "CU Type" - "cu_type", "PIM, PAM, POM, CHPIDs" -
             "enabled_chipids" and "installed_chipids"
             "Use" is mapped as "status" and its value is
             mapped as "online" or "offline"
    """
    if device:
        try:
            status = 'offline'
            if device[LSCSS_USE] == 'yes':
                status = 'online'
            device['status'] = status
            del device[LSCSS_USE]
            device['device'] = device.pop(LSCSS_DEV)
            device['sub_channel'] = device.pop(LSCSS_SUBCH)
            device['device_type'] = device.pop(LSCSS_DEVTYPE)
            device['cu_type'] = device.pop(LSCSS_CUTYPE)
            pim = device.pop(LSCSS_PIM)
            pam = device.pop(LSCSS_PAM)
            del device[LSCSS_POM]
            chipid = device.pop(LSCSS_CHPID)
            if pim == pam:
                binaryval_pam = _hex_to_binary(pam)
                device['enabled_chipids'] = _get_paths(binaryval_pam, chipid)
                device['installed_chipids'] = device['enabled_chipids']
            else:
                binaryval_pam = _hex_to_binary(pam)
                device['enabled_chipids'] = _get_paths(binaryval_pam, chipid)
                binaryval_pim = _hex_to_binary(pim)
                device['installed_chipids'] = _get_paths(binaryval_pim, chipid)
        except KeyError as e:
            wok_log.error('Issue while formating lscss dictionary output')
            raise e
    return device


def _byte_to_binary(n):
    """
    Converts each byte into binary value i.e. sets of 0 and 1
    """
    return ''.join(str((n & (1 << i)) and 1) for i in reversed(range(8)))


def _hex_to_binary(h):
    """
    Return the actual bytes of data represented by the
    hexadecimal string specified as the parameter.
    """
    return ''.join(_byte_to_binary(ord(b)) for b in binascii.unhexlify(h))


def _get_paths(mask, chipid):
    """
    method to return the enabled or installed paths of chipid.
    :param mask: the binary value for the pam or pim.
    :return: list of available or installed paths of the chipid value.
    """
    chipids = [chipid[i:i+2] for i in range(0, len(chipid), 2)]
    chipid_paths = []
    for index, j in enumerate(mask):
        if j == '1':
            chipid_paths.append(chipids[index])
    return chipid_paths


def _get_deviceinfo(lscss_out, device):
    """
    :param lscss_out: out of lscss command
    :param device: device id for which we need info to be returned
    :return: device info dict for the device from lscss output
    """
    device_pattern = r'('+re.escape(device) + r')\s+' \
                                              r'(\d\.\d\.[0-9a-fA-F]{4})\s+' \
                                              r'(\w+\/\w+)\s+' \
                                              r'(\w+\/\w+)\s' \
                                              r'(\s{3}|yes)\s+' \
                                              r'([0-9a-fA-F]{2})\s+' \
                                              r'([0-9a-fA-F]{2})\s+' \
                                              r'([0-9a-fA-F]{2})\s+' \
                                              r'(\w+\s\w+)'
    if device:
        device = utils.get_row_data(lscss_out, HEADER_PATTERN, device_pattern)
        msg = 'The device is %s' % device
        wok_log.debug(msg)
        try:
            device_info = _format_lscss(device)
            return device_info
        except KeyError as e:
            wok_log.error('lscss column key not found')
            raise e
    else:
        return device


def _list_devicesinfo(devicesinfo_dict, paths):
    """
    :param devicesinfo_dict: dict with key as device id and
            value as dict having all device info
    :param paths:list of device paths along with device Ids
    :return:list of dictionaries for the devices
            present in devicesinfo_dict and paths
    """
    devicesinfo = []
    if devicesinfo_dict and paths:
        for path in paths:
            device = utils.get_dirname(path)
            key = devicesinfo_dict.get(device)
            if key:
                devicesinfo.append(key)
    return devicesinfo


def _validate_device(device):
    """
    validate the device id. Valid device Ids should have
    <single digitnumber>.<single digitnumber>.<4 digit hexadecimalnumber>
    or <4 digit hexadecimal number>
    :param device: device id
    """
    pattern_with_dot = r'^\d\.\d\.[0-9a-fA-F]{4}$'
    if device and not str(device).isspace():
        device = str(device).strip()
        if "." in device:
            out = re.search(pattern_with_dot, device)
        else:
            device = '0.0.' + device
            out = re.search(pattern_with_dot, device)
        if out is None:
            wok_log.error("Invalid device id. Device: %s" % device)
            raise InvalidParameter("GS390XINVINPUT",
                                   {'reason': 'invalid device id: %s'
                                              % device})
    else:
        wok_log.error("Device id is empty. Device: %s" % device)
        raise InvalidParameter("GS390XINVINPUT",
                               {'reason': 'device id is required. Device: %s'
                                          % device})
    return device


def _device_online(device):
    """
    Bring device online, if it is not online.
    On success, if device is dasd-eckd and if it is not present in DASD_CONF
    then add it in DASD_CONF file.
    And if failed to add it, then bring the device in previous state.
    :param device: device id
    """
    with RollbackContext() as rollback:
        if not _is_online(device):
            _bring_online(device)
            rollback.prependDefer(_bring_offline, device)
        if _is_dasdeckd_device(device):
            if not _is_dasdeckd_persisted(device):
                _persist_dasdeckd_device(device)
        if _is_zfcp_device(device):
            _persist_zfcp_device(device)
        rollback.commitAll()


def _device_offline(device):
    """
    Bring device offline, if it is not offline.
    On success, if device is dasd-eckd and if it is present in DASD_CONF then
    remove it from DASD_CONF file.
    And if failed to remove it, then bring the device in previous state.
    :param device: device id
    """
    with RollbackContext() as rollback:
        if _is_online(device):
            _bring_offline(device)
            rollback.prependDefer(_bring_online, device)
        if _is_dasdeckd_device(device):
            if _is_dasdeckd_persisted(device):
                _unpersist_dasdeckd_device(device)
        if _is_zfcp_device(device):
            _unpersist_zfcp_device(device)
        rollback.commitAll()


def _get_dasdeckd_devices():
    """
    Return list of dasd-eckd devices
    """
    device_paths = utils.get_directories(syspath_eckd)
    dasdeckd_devices = []
    for path in device_paths:
        device = utils.get_dirname(path)
        if device:
            dasdeckd_devices.append(device)
    return dasdeckd_devices


def _get_zfcp_devices():
    """
    Return list of zfcp devices
    """
    device_paths = utils.get_directories(syspath_zfcp)
    zfcp_devices = []
    for path in device_paths:
        device = utils.get_dirname(path)
        if device:
            zfcp_devices.append(device)
    return zfcp_devices


def _is_online(device):
    """
    Return True if device is online, else return False
    :param device: device id
    """
    if os.access('/sys/bus/ccw/devices/%s/online' % device, os.R_OK):
        online_file = None
        try:
            online_file = open('/sys/bus/ccw/devices/%s/online' % device)
            value = online_file.readline()
            if value and value.strip() == '1':
                return True
        finally:
            if online_file:
                online_file.close()
    return False


def _is_dasdeckd_persisted(device):
    """
    Return True if device persent in DASD_CONF, else return False
    :param device: dasd-eckd device id
    """
    if os.access(DASD_CONF, os.R_OK):
        dasd_conf = None
        try:
            dasd_conf = open(DASD_CONF)
            dasd_conf.seek(0, 0)
            conf_content = dasd_conf.read()
            if re.search(br'(?i)%s' % device, conf_content):
                return True
        finally:
            if dasd_conf:
                dasd_conf.close()
    return False


def _bring_online(device):
    """
    Bring the device online
    :param device: device id
    """
    command_online = [chccwdev, '-e', device]
    out, err, rc = run_command(command_online)
    if rc:
        err = ','.join(line.strip() for line in err.splitlines())
        wok_log.error("Failed to bring device %s online. Error: %s"
                      % (device, err))
        raise OperationFailed("GS390XIOST001E",
                              {'device': device, 'error': err})


def _bring_offline(device):
    """
    Bring the device offline
    :param device: device id
    """
    command_offline = [chccwdev, '-d', device]
    out, err, rc = run_command(command_offline)
    if rc:
        err = ','.join(line.strip() for line in err.splitlines())
        wok_log.error("Failed to bring device %s offline. Error: %s"
                      % (device, err))
        raise OperationFailed("GS390XIOST004E",
                              {'device': device, 'error': err})


def _persist_dasdeckd_device(device):
    """
    Add the dasd-eckd device id into DASD_CONF
    :param device: device id
    """
    command_persist_dasdeckd = 'flock -w 1 %s -c \"echo %s >> %s\"' \
                               % (DASD_CONF, device, DASD_CONF)
    if os.access(DASD_CONF, os.W_OK):
        retcode = os.system(command_persist_dasdeckd)
        if not retcode:
            return
    wok_log.error("Failed to persist dasd-eckd device: %s" % device)
    raise OperationFailed("GS390XIOST002E", {'device': device})


def _unpersist_dasdeckd_device(device):
    """
    Remove the dasd-eckd device id from DASD_CONF
    :param device: device id
    """
    command_unpersist_dasdeckd = 'flock -w 1 %s -c \"sed -i \'/%s/Id\' %s\"'\
                                 % (DASD_CONF, device, DASD_CONF)
    if os.access(DASD_CONF, os.W_OK):
        retcode = os.system(command_unpersist_dasdeckd)
        if not retcode:
            return
    wok_log.error("Failed to unpersist dasd-eckd device: %s" % device)
    raise OperationFailed("GS390XIOST003E", {'device': device})


def _is_dasdeckd_device(device):
    """
    Return True if the device is of type dasd-eckd otherwise False
    :param device: device id
    """
    dasdeckd_devices = _get_dasdeckd_devices()
    if device in dasdeckd_devices:
        return True
    return False


def _is_zfcp_device(device):
    """
    Return True if the device is of type zfcp otherwise False
    :param device: device id
    """
    zfcp_devices = _get_zfcp_devices()
    if device in zfcp_devices:
        return True
    return False


def _persist_zfcp_device(device):
    """
    Add the zfcp device id and dummy lun info into ZFCP_CONF
    :param device: device id
    """
    dummy_lun_info = '0x0000000000000000 0x0000000000000000'
    persist_data = device + ' ' + dummy_lun_info
    command_persist_zfcp = 'flock -w 1 %s -c \"echo %s >> %s\"' \
                           % (ZFCP_CONF, persist_data, ZFCP_CONF)
    if os.access(ZFCP_CONF, os.W_OK):
        retcode = os.system(command_persist_zfcp)
        if not retcode:
            return
    wok_log.error("Failed to persist zfcp device: %s" % device)
    raise OperationFailed("GS390XIOST005E", {'device': device})


def _unpersist_zfcp_device(device):
    """
    Remove the zfcp device entry from ZFCP_CONF
    :param device: device id
    """
    command_unpersist_zfcp = 'flock -w 1 %s -c \"sed -i \'/%s/Id\' %s\"'\
                             % (ZFCP_CONF, device, ZFCP_CONF)
    if os.access(ZFCP_CONF, os.W_OK):
        retcode = os.system(command_unpersist_zfcp)
        if not retcode:
            return
    wok_log.error("Failed to unpersist zfcp device: %s" % device)
    raise OperationFailed("GS390XIOST006E", {'device': device})
