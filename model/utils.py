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


import ConfigParser
import glob
import re
import os

from ConfigParser import ParsingError
from wok.exception import OperationFailed, InvalidParameter
from os import listdir
from wok.utils import run_command, wok_log

res_hash = {}
adapters = []
ports = []

adapter_dir = '/sys/bus/ccw/drivers/zfcp/'
wlun = "0xc101000000000000"
lun0 = "0x0000000000000000"
sg_dir = "/sys/class/scsi_generic/"
udevadm = "/sbin/udevadm"
scsi_dir = '/sys/bus/scsi/devices/'


def update_lun_dict(lun_dict, adapter, port, fcp_lun):
    sg_dev = get_sg_dev(adapter, port, fcp_lun)
    if adapter not in lun_dict:
        lun_dict[adapter] = {}
    wwpn_lun_dict = {port: {}}
    if port not in lun_dict[adapter]:
        lun_dict[adapter].update(wwpn_lun_dict)
    fcp_lun_dict = {fcp_lun: sg_dev}
    out, err, rc = run_command(['sg_luns', '-m', '32768', '/dev/' + sg_dev])
    if rc == 0:
        luns = parse_sg_luns(out)
        for lun in luns:
            if lun == fcp_lun:
                continue
            fcp_lun_dict.update({lun: None})
    else:
        wok_log.error(
            "Error getting sg_luns for sg device. %s", sg_dev)
    lun_dict[adapter][port].update(fcp_lun_dict)
    return lun_dict


def _get_lun_dict():
    """
    Get the dictionary of LUNs configured on the system.
    :return: Dictionary containing discovered LUNs and their attributes
    """
    lun_dict = {}

    # Get the list of sg devices of configured LUNs (FC)
    sg_devices = get_sg_devices()

    # Iterate over all FC sg devices
    for sg_dev in sg_devices:
        wwpn = open(sg_dir + "/" + sg_dev + "/device/wwpn").readline().rstrip()
        fcp_lun = open(
            sg_dir +
            "/" +
            sg_dev +
            "/device/fcp_lun").readline().rstrip()
        hba_id = open(
            sg_dir +
            "/" +
            sg_dev +
            "/device/hba_id").readline().rstrip()

        if hba_id not in lun_dict:
            lun_dict[hba_id] = {}

        wwpn_lun_dict = {wwpn: {}}
        if wwpn not in lun_dict[hba_id]:
            lun_dict[hba_id].update(wwpn_lun_dict)

        fcp_lun_dict = {fcp_lun: sg_dev}

        # Lets see what other LUNs we can disocover using LUN 0
        if fcp_lun == lun0 or fcp_lun == wlun:
            out, err, rc = run_command(['sg_luns', '/dev/' + sg_dev])
            if rc == 0:
                luns = parse_sg_luns(out)
                for lun in luns:
                    if lun == fcp_lun:
                        continue
                    fcp_lun_dict.update({lun: None})
            else:
                wok_log.error(
                    "Error getting sg_luns for sg device. %s", sg_dev)
                # Not raising any exception here. The code should
                # continue to work for other LUNs even if it fails for
                # this LUN. That way we could grab as much info as
                # possible from system.

        if fcp_lun not in lun_dict[hba_id][wwpn]:
            lun_dict[hba_id][wwpn].update(fcp_lun_dict)

    return lun_dict


def _get_sg_inq_dict(sg_inq_output):
    """
    Parse the output of 'sg_inq' command against the the relavant sg_device
    :param sg_inq_output: Output of the command 'sg_inq' on sg_devic3
    :return: Dictinary of parsed 'sg_inq' output
    """

    sg_inq_dict = {}

    if not sg_inq_output:
        sg_inq_dict['status'] = 'offline'
    else:
        sg_inq_dict['status'] = 'online'

    try:
        pattern = r'Peripheral device type:\s+(.+)'
        m = re.search(pattern, sg_inq_output)
        disk_type = m.group(1)
        if disk_type == "storage array controller" \
                or disk_type == 'well known logical unit':
            sg_inq_dict['type'] = 'disk'
        else:
            sg_inq_dict['type'] = disk_type

        pattern = r'Vendor identification:\s+(\S+)'
        m = re.search(pattern, sg_inq_output)
        sg_inq_dict['vendor'] = m.group(1)

        pattern = r'Product identification:\s+(\S+)'
        m = re.search(pattern, sg_inq_output)
        sg_inq_dict['product'] = m.group(1)

        pattern = r'Unit serial number:\s+(.+)'
        m = re.search(pattern, sg_inq_output)
        if m:
            sg_inq_dict['controllerSN'] = m.group(1)
        else:
            sg_inq_dict['controllerSN'] = 'N/A'
    except:
        wok_log.error("Error parsing sg_luns. %s", sg_inq_output)
        # Not raising any exception here. The code should
        # continue to work for other LUNs even if it fails for
        # this LUN. That way we could grab as much info as
        # possible from system.

    return sg_inq_dict


def clear_multipath(dm_long_name):
    """
    Clear a multipath device entry
    @param dm_long_name : name of multipath device
    """
    out, err, rc = run_command(['multipath', '-f', dm_long_name])
    if rc != 0:
        wok_log.error("Unable to remove multipath device, %s", dm_long_name)
        raise OperationFailed("GS390XSTG0018E", {'err': err})


def find_other_paths(sg_device):
    """
    Find the other paths of to the same disk
    @param sg_device: sg device to find paths from.
    @return : list of tuples represeting each path
    """
    other_paths = []
    sg_dev_path = sg_dir + "/" + sg_device
    dm_slaves = []
    try:
        block_dev = os.listdir(sg_dev_path + "/device/block/")[0]
        dm_dev = os.listdir(
            sg_dev_path +
            "/device/block/" +
            block_dev +
            "/holders/")[0]
        dm_slaves_path = sg_dev_path + "/device/block/" + \
            block_dev + "/holders/" + dm_dev + "/slaves"
        dm_slaves = os.listdir(dm_slaves_path)
        dm_slaves.remove(block_dev)
    except:
        # Either the dm device associated with this device
        # is removed or some other thread issued 'multipath -f device'
        # It's alright to continue normally in that case.
        pass

    for dm_slave in dm_slaves:
        try:
            dm_slave_device_path = dm_slaves_path + "/" + dm_slave + "/device"

            wwpn = open(dm_slave_device_path + "/wwpn").readline().rstrip()
            fcp_lun = open(
                dm_slave_device_path +
                "/fcp_lun").readline().rstrip()
            hba_id = open(
                dm_slave_device_path +
                "/hba_id").readline().rstrip()
            other_paths.append((hba_id, wwpn, fcp_lun))
        except:
            # Some other thread might have deleted the path
            # that we are trying to delete. Just move on with
            # normal flow from here.
            pass

    return other_paths


def remove_lun(adapter, port, lun_id):
    """
    Remove a LUN from system
    :param adapter: HBA adapter id
    :param port: Remote port wwpn
    :param lun_id: Id of the given LUN
    """
    luns = []

    # get lun information using lszfcp -l
    out, err, rc = run_command(['lszfcp', '-l', lun_id])
    if out:
        parsed_zfcp_out = parse_lszfcp_out(out)
        if parsed_zfcp_out and isinstance(parsed_zfcp_out, dict):
            for path, scsi_dev in parsed_zfcp_out.iteritems():
                dm_long_name = None
                try:
                    path = path.split('/')
                    luns.append((path[0], path[1], path[2]))

                    scsi_dev_dir = scsi_dir + scsi_dev
                    block_dev = os.listdir(scsi_dev_dir + "/block/")[0]
                    dm_dev = os.listdir(
                        scsi_dev_dir +
                        "/block/" +
                        block_dev +
                        "/holders/")[0]
                    with open(scsi_dev_dir + "/block/" +
                              block_dev + "/holders/" +
                              dm_dev + "/dm/name", 'r') as txt_file:
                        dm_long_name = txt_file.readline().rstrip()

                except:
                    # It may happen that the given device may not have
                    # a corresponding dm device. In that case just
                    # move on without doing anything.
                    pass
                if dm_long_name:
                    clear_multipath(dm_long_name)
                remove_auto_lun(scsi_dev)

    else:
        # try checking sg entries in scci_generic
        # Let's look for the sg_device associated with this LUN
        sg_dev = get_sg_dev(adapter, port, lun_id)
        if sg_dev:
            luns.append((adapter, port, lun_id))
            sg_device = sg_dev
            sg_dev_path = sg_dir + "/" + sg_device
            other_paths = find_other_paths(sg_device)
            for op in other_paths:
                hba_id = op[0]
                wwpn = op[1]
                fcp_lun = op[2]
                luns.append((hba_id, wwpn, fcp_lun))
            dm_long_name = None
            try:
                block_dev = os.listdir(sg_dev_path + "/device/block/")[0]
                dm_dev = os.listdir(
                    sg_dev_path +
                    "/device/block/" +
                    block_dev +
                    "/holders/")[0]
                dm_long_name = open(
                    sg_dev_path +
                    "/device/block/" +
                    block_dev +
                    "/holders/" +
                    dm_dev +
                    "/dm/name").readline().rstrip()
            except:
                # It may happen that the given device may not have
                # a corresponding dm device. In that case just
                # move on without doing anything.
                pass
            if dm_long_name:
                clear_multipath(dm_long_name)

    for lun in luns:
        port_dir = '/sys/bus/ccw/drivers/zfcp/' + lun[0] + '/' + lun[1] + '/'
        lun_dir = port_dir + lun[2]
        wok_log.info("Removing LUN, %s", lun_dir)

        if not os.path.exists(lun_dir):
            continue  # move on... some other thread removed this LUN already

        try:
            with open(port_dir + 'unit_remove', "w") as txt_file:
                txt_file.write(lun[2])

            fo = open("/etc/zfcp.conf", "r")
            lines = fo.readlines()
            output = []
            fo.close()
            fo = open("/etc/zfcp.conf", "w")
            for line in lines:
                if [lun[0], lun[1], lun[2]] == line.split():
                    continue
                else:
                    output.append(line)
            fo.writelines(output)
            fo.close()
        except Exception as e:
            wok_log.error("Unable to remove LUN, %s", lun_dir)
            raise OperationFailed("GS390XSTG00002", {'err': e.message})


def add_lun(adapter, port, lun_id):
    """
    Add a LUN to system
    :param adapter: HBA adapter id
    :param port: Remote port wwpn
    :param lun_id: Id of the given LUN
    """

    port_dir = '/sys/bus/ccw/drivers/zfcp/' + adapter + '/' + port + '/'
    lun_dir = port_dir + lun_id

    wok_log.info("Adding LUN, %s", lun_dir)

    if os.path.exists(lun_dir):
        # LUN already present on the system, nothing to add.
        return
    else:
        try:
            with open(port_dir + 'unit_add', "w") as txt_file:
                txt_file.write(lun_id)

            for _ in range(4):
                # Don't wait for udev queue to completely flush.
                # Wait for the relavant entry for this LUN is created in sysfs
                run_command([udevadm, "settle", "--exit-if-exists=" + lun_dir])
                if os.path.exists(lun_dir):
                    entry_exists = False
                    fo = open("/etc/zfcp.conf", "r")
                    lines = fo.readlines()
                    for line in lines:
                        if [adapter, port, lun_id] == line.split():
                            entry_exists = True
                    fo.close()
                    if not entry_exists:
                        with open("/etc/zfcp.conf", "a") as zfcp:
                            zfcp.write(
                                adapter + " " + port + " " + lun_id + "\n")
                    break

        except Exception as e:
            wok_log.error("Unable to add LUN, %s", lun_dir)
            raise OperationFailed("GS390XSTG00003", {'err': e.message})


def get_lun_info(adapter, port, lun_id):
    """
    Get detailed information about a specific LUN
    :param adapter: HBA adapter id
    :param port: Remote port wwpn
    :param lun_id: Id of the given LUN
    :return: Dictionary containing detailed information about a specific LUN
    """

    port_dir = '/sys/bus/ccw/drivers/zfcp/' + adapter + '/' + port + '/'
    lun_dir = port_dir + lun_id

    lun_info = {}

    out, err, rc = run_command(['lszfcp', '-l', lun_id])

    parsed_lszfcp_out = parse_lszfcp_out(out)
    lszfcp_key = adapter + '/' + port + '/' + lun_id

    if lszfcp_key in parsed_lszfcp_out.keys() or os.path.exists(lun_dir) \
            or is_lun_scan_enabled()['current']:
        lun_info['configured'] = True
    else:
        lun_info['configured'] = False

        try:
            with open(port_dir + 'unit_add', "w") as txt_file:
                txt_file.write(lun_id)

            for _ in range(4):
                run_command([udevadm, "settle", "--exit-if-exists=" + lun_dir])
                if os.path.exists(lun_dir):
                    break

            if not os.path.exists(lun_dir):
                with open(port_dir + 'unit_remove', "w") as txt_file:
                    txt_file.write(lun0)

                with open(port_dir + 'unit_add', "w") as txt_file:
                    txt_file.write(wlun)

                for _ in range(4):
                    run_command(
                        [udevadm, "settle", "--exit-if-exists=" + lun_dir])

                    if os.path.exists(lun_dir):
                        break

                    if not os.path.exists(lun_dir):
                        with open(port_dir + 'unit_remove', "w") as txt_file:
                            txt_file.write(wlun)

        except Exception as e:
            if 'Invalid argument' in e or 'No such file or directory' in e:
                raise InvalidParameter("GS390XSTG00022")
            wok_log.error("Unable to add LUN temporarily, %s", lun_dir)
            raise OperationFailed("GS390XSTG00003", {'err': e.message})

    # Get the list of FC only sg devices. This includes the sg_devices
    # of temporary LUNs as well.
    sg_devices = get_sg_devices()
    for sg_dev in sg_devices:
        try:
            wwpn = open(
                sg_dir +
                "/" +
                sg_dev +
                "/device/wwpn").readline().rstrip()
            fcp_lun = open(
                sg_dir +
                "/" +
                sg_dev +
                "/device/fcp_lun").readline().rstrip()
            hba_id = open(
                sg_dir +
                "/" +
                sg_dev +
                "/device/hba_id").readline().rstrip()

            if hba_id == adapter and wwpn == port and fcp_lun == lun_id:
                lun_info['hbaId'] = hba_id
                lun_info['remoteWwpn'] = port
                lun_info['lunId'] = lun_id

                lun_info['sgDev'] = sg_dev
                out, err, rc = run_command(["sg_inq", "/dev/" + sg_dev])
                if rc == 0:
                    lun_info.update(_get_sg_inq_dict(out))
                break

        except:
            # While looking for relavent sg_device in an multithreaded
            # environment it may happen that the directory we are looking
            # into might get deleted by another thread. In this was just
            # just skip this current directory and look for the sg_device
            # somewhere else. This is why we should just pass this
            # exception.
            pass

    # Get rid of the LUN if it's not configured
    if not lun_info['configured']:
        lun_info['configured'] = "false"
        try:
            wok_log.info("Removing sg_device , %s", lun_info['sgDev'])
            with open(sg_dir + lun_info['sgDev'] + '/device/delete', "w")\
                    as txt_file:
                txt_file.write("1")

            del lun_info['sgDev']

        except Exception as e:
            wok_log.error("Unable to remove sg_device , %s", lun_info['sgDev'])
            raise OperationFailed("GS390XSTG00001", {'err': e.message})

        try:
            wok_log.info("Removing LUN , %s", lun_dir)
            with open(port_dir + 'unit_remove', "w") as txt_file:
                txt_file.write(fcp_lun)
        except:
            # If failed to remove the given LUN, at least remove the wlun
            wok_log.info("Removing LUN , %s", port_dir + ":" + wlun)
            try:
                with open(port_dir + 'unit_remove', "w") as txt_file:
                    txt_file.write(wlun)
            except:
                # Just logging is sufficient. No need to raise exception and
                # stop the code flow
                wok_log.error(
                    "Removing LUN failed , %s",
                    port_dir + ":" + wlun)
    else:
        lun_info['configured'] = "true"

    return lun_info


def get_sg_devices():
    """
    Returns the list of FC only 'sg' devices.
    :return List of FC only sg_devices
    """

    sg_devices = []
    for sg_dev in listdir(sg_dir):

        # skip devices whose transport is not FC
        if os.path.exists(sg_dir + "/" + sg_dev + "/device/wwpn"):
            sg_devices.append(sg_dev)

    return sg_devices


def get_sg_dev(adapter, port, lun_id):
    """
    Find the corresponding sg_device for the given LUN
    :param adapter:
    :param port:
    :param lun_id:
    :return:
    """
    sg_device = None

    sg_devices = get_sg_devices()
    for sg_dev in sg_devices:
        try:
            wwpn = open(sg_dir + "/" + sg_dev +
                        "/device/wwpn").readline().rstrip()
            fcp_lun = open(
                sg_dir +
                "/" +
                sg_dev +
                "/device/fcp_lun").readline().rstrip()
            hba_id = open(
                sg_dir +
                "/" +
                sg_dev +
                "/device/hba_id").readline().rstrip()

            if hba_id == adapter and wwpn == port and fcp_lun == lun_id:
                sg_device = sg_dev
                break
        except:
            # While looking for relavent sg_device in an multithreaded
            # environment it may happen that the directory we are looking
            # into might get deleted by another thread. In this was just
            # just skip this current directory and look for the sg_device
            # somewhere else. This is why we should just pass this
            # exception.
            pass

    return sg_device


def _get_host_fcp_dict():
    """
    Get the dictionary containing the host HBAs and
    corresponding remote ports
    :return: HBA -> LUNs dictionary
    """
    host_fcp_dict = {}

    adapters = glob.glob(adapter_dir + '*.*.*')

    for adapter in adapters:
        a = adapter.split('/')[-1]
        host_fcp_dict[a] = []

        ports = glob.glob(adapter + '/0x*')

        for port in ports:
            b = port.split('/')[-1]
            host_fcp_dict[a].append(b)

    return host_fcp_dict


def get_luns():
    """
    Get the list of all the LUNs including unconfigured ones
    :return: List of all the LUN paths
    """
    lun_info_list = []
    if is_lun_scan_enabled()['current']:
        return lun_info_list

    out, err, rc = run_command(['lszfcp', '-D'])

    if rc:
        wok_log.error('Error in lszfcp -D command,  %s', err)

    parsed_lszfcp_out = parse_lszfcp_out(out)

    host_fcp_dict = _get_host_fcp_dict()
    global lun_dict
    lun_dict = _get_lun_dict()

    # Loop over all HBA adapters
    for adapter in host_fcp_dict:
        # Loop over every remote port for the given HBA adapter
        for port in host_fcp_dict[adapter]:
            temp_luns = {}
            port_dir = adapter_dir + adapter + '/' + port + '/'

            # If port went offline or is not accessible, skip.
            if not os.path.exists(port_dir):
                continue

            access_denied = open(
                port_dir + 'access_denied').readline().rstrip()
            if access_denied == "1":
                continue

            failed = open(port_dir + 'failed').readline().rstrip()
            if failed == "1":
                continue

            in_recovery = open(port_dir + 'in_recovery').readline().rstrip()
            if in_recovery == "1":
                continue

            # If no LUNs are associated with this port, try adding LUN 0
            # to initiate LUN discovery on this port later
            add_discovery_lun = False
            if adapter not in lun_dict or port not in lun_dict[adapter]:
                add_discovery_lun = True

            if adapter in lun_dict and port in lun_dict[adapter]:
                port_luns_keys = lun_dict[adapter][port]
                add_discovery_lun = True
                for lun_key in port_luns_keys:
                    if lun_key == lun0 or lun_key == wlun:
                        add_discovery_lun = False

            if add_discovery_lun:
                try:
                    with open(port_dir + 'unit_add', "w") as txt_file:
                        txt_file.write(lun0)

                    run_command(
                        [udevadm, "settle",
                         "--exit-if-exists=" + port_dir + lun0])
                    update_luns = True
                    temp_luns[lun0] = True
                    if os.path.exists(port_dir + lun0):
                        failed = open(
                            port_dir + lun0 + '/failed').readline().rstrip()
                        if failed == "1":
                            update_luns = False
                            if adapter in lun_dict and port in lun_dict[
                                    adapter]:
                                del lun_dict[adapter][port]
                    if update_luns:
                        lun_dict = update_lun_dict(
                            lun_dict, adapter, port, lun0)

                except Exception as e:
                    wok_log.error("Unable to add LUN 0 , %s", port_dir + lun0)

                if adapter not in lun_dict or port not in lun_dict[adapter]:
                    try:
                        with open(port_dir + 'unit_remove', "w") as txt_file:
                            txt_file.write(lun0)
                        temp_luns[lun0] = False

                    except Exception as e:
                        wok_log.error(
                            "Unable to remove LUN 0 , %s", port_dir + lun0)

                    try:
                        with open(port_dir + 'unit_add', "w") as txt_file:
                            txt_file.write(wlun)

                        run_command(
                            [udevadm, "settle",
                             "--exit-if-exists=" + port_dir + "/" + wlun])
                        lun_dict = update_lun_dict(
                            lun_dict, adapter, port, wlun)
                        temp_luns[wlun] = True

                    except Exception as e:
                        wok_log.error(
                            "Unable to add wlun , %s", port_dir + wlun)

                    if adapter not in lun_dict or port not in lun_dict[
                            adapter]:
                        try:
                            with open(port_dir + 'unit_remove', "w")\
                                    as txt_file:
                                txt_file.write(wlun)
                            temp_luns[wlun] = False
                            continue

                        except Exception as e:
                            wok_log.error(
                                "Unable to remove wlun , %s", port_dir + wlun)

            disc_sg_dev = ''
            if lun0 in lun_dict[adapter][port]:
                disc_sg_dev = lun_dict[adapter][port][lun0]
            if wlun in lun_dict[adapter][port]:
                disc_sg_dev = lun_dict[adapter][port][wlun]
            try:
                if disc_sg_dev:
                    out, err, rc = run_command(
                        ["sg_inq", "/dev/" + disc_sg_dev])
                    if rc == 0:
                        for lun in lun_dict[adapter][port]:
                            if lun == wlun:
                                continue
                            port_dir = '/sys/bus/ccw/drivers/zfcp/' +\
                                adapter + '/' + port + '/'
                            lun_dir = port_dir + lun
                            lun_info_dict = {}
                            lun_info_dict.update(_get_sg_inq_dict(out))
                            lun_info_dict['hbaId'] = adapter
                            lun_info_dict['remoteWwpn'] = port
                            lun_info_dict['lunId'] = lun
                            lszfcp_key = adapter + '/' + port + '/' + lun
                            if lszfcp_key in parsed_lszfcp_out.keys()\
                               or os.path.exists(lun_dir):
                                if lun in temp_luns and temp_luns[lun] is True:
                                    lun_info_dict['configured'] = "false"
                                else:
                                    lun_info_dict['configured'] = "true"
                            else:
                                lun_info_dict['configured'] = "false"
                            lun_info_list.append(lun_info_dict)
            except Exception as e:
                wok_log.error(
                    "Unable to get sg dev for discovery lun, %s", lun_dir)
                raise OperationFailed("GS390XSTG00021", {'err': e.message})

            if adapter in lun_dict and port in lun_dict[adapter]:
                for lun in lun_dict[adapter][port]:

                    # Get rid of the LUN if added temporarily for discovery
                    if lun in temp_luns and temp_luns[lun] is True:
                        sg_dev = ''
                        if port in lun_dict[
                                adapter] and lun in lun_dict[adapter][port]:
                            sg_dev = lun_dict[adapter][port][lun]

                        if sg_dev:
                            try:
                                wok_log.info("Removing LUN 0, %s", port_dir)
                                with open(port_dir + 'unit_remove', "w")\
                                        as txt_file:
                                    txt_file.write(lun0)
                            except:
                                wok_log.error(
                                    "unable to remove LUN 0, %s", port_dir)
                                wok_log.info("Removing wlun,  %s", wlun)
                                try:
                                    with open(port_dir + 'unit_remove', "w")\
                                            as txt_file:
                                        txt_file.write(wlun)
                                except:
                                    # Can be safely ingored, so not raising
                                    # exception
                                    wok_log.error(
                                        "unable to remove wlun, %s", port_dir)

                        temp_luns[lun] = False

    return lun_info_list


def parse_sg_luns(sg_luns_output):
    """
    Parse the output of 'sg_luns' command on the given sg_device
    :param sg_luns_output: Output of sg_luns command
    return: Dictionary containing parsed output
    """

    # Take out LUN IDs of all discovered LUNs
    pattern = re.compile(r'([a-zA-Z0-9]{16})')
    match = pattern.findall(sg_luns_output)
    match = ['0x' + i for i in match]
    # By default returns empty list if no match found

    return match


def validate_lun_path(lun_path):
    """
    Validate the LUN path and return the list of LUN path components
    :param lun_path: Path to access the LUN
    :return : List containing the LUN path components
    """

    lun_path_list = []
    try:
        lun_path_list = lun_path.split(":")
    except Exception as e:
        wok_log.error("Unable to parse lun path components, %s", lun_path)
        raise InvalidParameter("GS390XSTG00004", {'err': e.message})

    validate_hba_id(lun_path_list[0])
    validate_wwpn_or_lun(lun_path_list[1])
    validate_wwpn_or_lun(lun_path_list[2])

    return lun_path_list


def validate_hba_id(hba_id):
    """
    Validate hba id which should be of form, 0.0.xxxx
    :param hba_id: HBA ID to be validated
    """
    pattern = re.compile(r'[0-2].[0-2].[a-z0-9]{4}')
    valid = pattern.match(hba_id)
    if not valid:
        wok_log.error("Unable to validate HBA ID, %s", hba_id)
        raise InvalidParameter(
            "GS390XSTG00005", {
                'err': 'Invalid HBA ID ' + hba_id})


def validate_wwpn_or_lun(input_id):
    """
    Validate wwpn or lun_id which should be of form, 0xaaaaaaaaaaaaaaaa.
    :param input_id: input_id to be validated
    """
    pattern = re.compile(r'0x[a-zA-Z0-9]{16}')
    valid = pattern.match(input_id)
    if not valid:
        wok_log.error("Unable to validate, %s", input_id)
        raise InvalidParameter(
            "GS390XSTG00006", {
                'err': 'Invalide wwpn or LUN ID'})


def is_lun_scan_enabled():
    """
    Detect if automatic LUN scanning is enabled or disabled
    :return : Dictionary containing LUN Scanning status
              on bootloader as well as on running system
    """
    lun_scan_status = {}
    try:

        config = ConfigParser.ConfigParser()
        config.read("/etc/zipl.conf")
        default_boot = config.get('defaultboot', 'default')
        boot_parameters = config.get(default_boot, 'parameters')

        pattern = r'.+zfcp\.allow_lun_scan=(\d)'

        m = re.search(pattern, boot_parameters)
        enabled = bool(int(m.group(1)))
        lun_scan_status['boot'] = enabled

    except ParsingError:
        check_zipl_file()
        is_lun_scan_enabled()
    except Exception as e:
        wok_log.error("Unable to parse /etc/zipl.conf")
        raise OperationFailed("GS390XSTG00013", {'err': e.message})

    try:
        run_time = open('/sys/module/zfcp/parameters/allow_lun_scan')\
            .readline().rstrip()
        run_time = True if run_time == "Y" else False
        lun_scan_status['current'] = run_time

    except Exception as e:
        wok_log.error("Error reading the file")
        lun_scan_status['current'] = False

    return lun_scan_status


def check_zipl_file():
    """
    Look for indented text in /etc/zipl.conf file and remove spaces if found
    :return:
    """
    f = open('/etc/zipl.conf', 'r')
    lines = f.readlines()
    f.close()

    # rewrite the file removing the spaces if any
    f = open('/etc/zipl.conf', 'w')
    for line in lines:
        p = re.match('^\s+\S', line)
        if p:
            line = line.lstrip()
        f.write(line)
    f.close()


def enable_lun_scan(enable):
    """
    Set automatic LUN scanning enabled or disabled
    :param enable: "0" to disable, "1" to enable
    """

    if enable not in ["1", "0"]:
        raise Exception("argument has to '0' or '1'")

    try:
        zipl_file = "/etc/zipl.conf"
        boot_param = "zfcp.allow_lun_scan"
        config = ConfigParser.ConfigParser()
        config.read(zipl_file)
        default_boot = config.get('defaultboot', 'default')
        boot_parameters = config.get(default_boot, 'parameters')

        # Modify boot parameter, zfcp.allow_lun_scan
        boot_parameters = modify_boot_param(
            boot_parameters, boot_param, enable)
        config.set(default_boot, 'parameters', boot_parameters)

        with open(zipl_file, "wb") as config_file:
            config.write(config_file)

        # Update the bootloader
        run_zipl_cmd()

    except Exception as e:
        wok_log.error("Unable to parse /etc/zipl.conf")
        raise OperationFailed("GS390XSTG00013", {'err': e.message})

    try:
        # Enable/Disable LUN Scanning on a running system
        wrt_msg = "Y" if enable == "1" else "N"
        with open('/sys/module/zfcp/parameters/allow_lun_scan', "w")\
                as txt_file:
            txt_file.write(wrt_msg)

    except Exception as e:
        wok_log.error("Failed to enable lunscanning in current zfcp module")
        raise OperationFailed("GS390XSTG00019", {'err': e.message})


def modify_boot_param(boot_params_string, boot_param, param_value):
    """
    Modify given boot parameters in /etc/zipl.conf
    :param boot_params_string: boot parameters string from /etc/zipl.conf
    :param boot_param : parameter to be modified
    :param param_value : new value of the parameter
    :return : Modified boot parameters string
    """

    boot_params_string = re.sub(
        boot_param + "=\S",
        boot_param + "=" + param_value,
        boot_params_string)

    if not boot_params_string:
        wok_log.error("Unable to find +" + boot_param + " in /etc/zipl.conf")
        raise OperationFailed("GS390XSTG00014", {'param': boot_param})

    return boot_params_string


def run_zipl_cmd():
    """
    Run zipl command to update the bootloader
    """

    wok_log.info('Running zipl command to update bootloader')
    out, err, rc = run_command(['zipl'])
    if rc:
        wok_log.error('failed to execute zipl,  %s', err)
        raise OperationFailed("GS390XSTG00015", {'err': err})


def trigger_lun_scan(cb, params):
    """
    Trigger LUN scanning
    """

    cb('')  # reset messages
    try:
        wok_log.info('Triggering LUN scan using rescan-ssci-bus.sh')
        out, err, rc = run_command(['/usr/bin/rescan-scsi-bus.sh', '-a'])
        if rc:
            wok_log.error('failed to trigger LUN scan,  %s', err)
            cb(err, False)

        cb('OK', True)
    except Exception as e:
        cb(e.message, False)


def get_final_tape_list():
    """
    Get the final list of all tape devices
    """
    out = run_lstape_scsi_cmd()
    return parse_tape_list(out)


def parse_tape_list(lstape_out):
    """
    Parse the output of the command lstape
    :param lstape_out : Output obtained by 'lstape' command
    """
    try:
        final_list = []
        input_list = lstape_out.splitlines()
        scsi_keys = input_list[0].split()

        for input_device in input_list[1:]:
            device_params = {}
            device_params_list = input_device.split()
            for scsi_key, device_param in zip(scsi_keys, device_params_list):
                device_params[scsi_key] = device_param
            final_list.append(device_params)

    except Exception as e:
        wok_log.error("Unable to parse output of lstape")
        raise OperationFailed("GS390XSTG00016", {'err': e.message})

    return final_list


def run_lstape_scsi_cmd():
    """
    Run 'lstape --scsi-only' command
    """

    wok_log.info('Running lstape command')
    out, err, rc = run_command(['lstape', '--scsi-only'])
    if rc:
        wok_log.error('failed to execute lstape,  %s', err)
        raise OperationFailed("GS390XSTG00017", {'err': err})

    return out


def parse_lszfcp_out(output):
    """
    This method is used to parse 'lszfcp -l lunid'
    sample output of 'lszfcp -l lunid':
    lszfcp -l 0x00c6000000000000
    0.0.3090/0x5005076802160417/0x00c6000000000000 0:0:0:198
    0.0.3090/0x5005076802260417/0x00c6000000000000 0:0:1:198
    :param output: output of lszfcp -l command
    :return:
    """
    output = output.strip().splitlines()
    scsi_dev_info = {}
    for line in output:
        line = line.strip().split()
        scsi_dev_info[line[0]] = line[-1]
    return scsi_dev_info


def remove_auto_lun(scsi_dev):
    """
    this method is to remove luns which were configured with lun scan enabled
    """
    delete_file = scsi_dir + scsi_dev + '/delete'
    try:
        with open(delete_file, 'w') as txt_file:
            txt_file.write("1")
    except:
        # some other thread might have removed the lun
        pass
