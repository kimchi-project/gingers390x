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


import utils

from wok.exception import (InvalidOperation,
                           MissingParameter,
                           NotFoundError,
                           OperationFailed
                           )
from wok.model.tasks import TaskModel
from wok.utils import add_task, wok_log


class LUNScanModel(object):
    """
    model class for ignore list
    """

    def __init__(self, **kargs):
        self.objstore = kargs.get('objstore')
        self.task = TaskModel(**kargs)

    def lookup(self, name):
        """
        Get the status of LUN scanning
        :return: returns dictionary with key as 'lunscan'
                and value as boolean
        """
        return utils.is_lun_scan_enabled()

    def enable(self, name):
        """
        Enable LUN scanning
        """
        utils.enable_lun_scan("1")
        return utils.is_lun_scan_enabled()

    def disable(self, name):
        """
        Disable LUN scanning
        """
        utils.enable_lun_scan("0")
        return utils.is_lun_scan_enabled()

    def trigger(self, name):
        """
        Trigger LUN scanning
        """
        taskid = add_task('/plugins/gingers390/lunscan/trigger',
                          utils.trigger_lun_scan, self.objstore, {})

        return self.task.lookup(taskid)


class FCLUNsModel(object):
    """
    Model representing the collection of FC LUNs
    """

    def __init__(self, **kargs):
        pass

    def create(self, params):
        if utils.is_lun_scan_enabled()['current']:
            wok_log.error(
                "Lun scan is enabled. Cannot add/remove LUNs manually.")
            raise InvalidOperation("GS390XSTG00009")

        if 'hbaId' not in params:
            wok_log.error("hbaId is required for adding a LUN")
            raise MissingParameter("GS390XSTG00010")

        hbaId = params['hbaId']
        utils.validate_hba_id(hbaId)

        if 'remoteWwpn' not in params:
            wok_log.error("remoteWwpn is required for adding a LUN")
            raise MissingParameter("GS390XSTG00011")

        wwpn = params['remoteWwpn']
        utils.validate_wwpn_or_lun(wwpn)

        if 'lunId' not in params:
            wok_log.error("lunId is required for adding a LUN")
            raise MissingParameter("GS390XSTG00012")

        lunId = params['lunId']
        utils.validate_wwpn_or_lun(lunId)

        utils.add_lun(hbaId, wwpn, lunId)

        lun_path = hbaId + ":" + wwpn + ":" + lunId
        return lun_path

    def get_list(self):
        try:
            return utils.get_luns()
        except OperationFailed as e:
            wok_log.error("Fetching list of LUNs failed")
            raise OperationFailed("GS390XSTG00007", {'err': e})


class FCLUNModel(object):
    """
    Model representing a single FC LUN
    """

    def __init__(self, **kargs):
        pass

    def lookup(self, path):
        try:
            path_components = utils.validate_lun_path(path)
            return utils.get_lun_info(*path_components)
        except ValueError:
            wok_log.error("Fetching LUN info failed, %s", path)
            raise NotFoundError("GS390XSTG00008", {'path': path})

    def delete(self, path):
        if utils.is_lun_scan_enabled()['current']:
            wok_log.error(
                "Lun scan is enabled. Cannot add/remote LUNs manually.")
            raise InvalidOperation("GS390XSTG00009")

        path_components = utils.validate_lun_path(path)
        utils.remove_lun(*path_components)
