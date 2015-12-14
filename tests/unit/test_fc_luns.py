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

import model.fc_luns as fc_luns
from wok.exception import InvalidOperation, InvalidParameter, MissingParameter
from model import utils


class FCLUNsTests(unittest.TestCase):
    """
    unit tests for FC LUNs
    """

    @mock.patch('model.fc_luns.wok_log', autospec=True)
    @mock.patch('model.fc_luns.utils.is_lun_scan_enabled', autospec=True)
    def test_create_lun_scan_enabled(self, mock_scan_enabled, mock_wok_log):
        mock_scan_enabled.return_value = {'current': True}

        params = {}
        params['hbaId'] = "0.0.2222"
        params['remoteWwpn'] = "0x1111111111111111"
        params['lunId'] = "0x2222222222222222"

        lun_model = fc_luns.FCLUNsModel()
        self.assertRaises(InvalidOperation, lun_model.create, params)

        msg = "Lun scan is enabled. Cannot add/remove LUNs manually."
        self.assertTrue(mock_wok_log.error.called, msg=msg)

    @mock.patch('model.fc_luns.wok_log', autospec=True)
    @mock.patch('model.fc_luns.utils.is_lun_scan_enabled', autospec=True)
    @mock.patch('model.fc_luns.utils.add_lun', autospec=True)
    def test_create_lun_scan_disabled1(
        self,
        mock_add_lun, mock_scan_enabled, mock_wok_log
    ):

        mock_add_lun.return_value = None
        mock_scan_enabled.return_value = {'current': False}

        params = {}
        params['remoteWwpn'] = "0x1111111111111111"
        params['lunId'] = "0x2222222222222222"

        lun_model = fc_luns.FCLUNsModel()
        self.assertRaises(MissingParameter, lun_model.create, params)
        self.assertTrue(mock_wok_log.error.called,
                        msg="hbaId is required for adding a LUN")

        params = {}
        params['hbaId'] = "0.0.2222"
        params['lunId'] = "0x2222222222222222"

        lun_model = fc_luns.FCLUNsModel()
        self.assertRaises(MissingParameter, lun_model.create, params)
        self.assertTrue(mock_wok_log.error.called,
                        msg="remoteWwpn is required for adding a LUN")

        params = {}
        params['hbaId'] = "0.0.2222"
        params['remoteWwpn'] = "0x1111111111111111"

        lun_model = fc_luns.FCLUNsModel()
        self.assertRaises(MissingParameter, lun_model.create, params)
        self.assertTrue(mock_wok_log.error.called,
                        msg="lunId is required for adding a LUN")

    def test_sg_inq_outout(self):
        sg_inq_output = """standard INQUIRY:
  PQual=0  Device_type=0  RMB=0  version=0x06  [SPC-4]
  [AERC=0]  [TrmTsk=0]  NormACA=1  HiSUP=1  Resp_data_format=2
  SCCS=0  ACC=0  TPGS=1  3PC=1  Protect=0  [BQue=0]
  EncServ=0  MultiP=1 (VS=0)  [MChngr=0]  [ACKREQQ=0]  Addr16=0
  [RelAdr=0]  WBus16=0  Sync=0  Linked=0  [TranDis=0]  CmdQue=1
  [SPI: Clocking=0x0  QAS=0  IUS=0]
    length=109 (0x6d)   Peripheral device type: disk
 Vendor identification: IBM
 Product identification: 2145
 Product revision level: 0000
 Unit serial number: 0200a0435412XX00
"""
        output_dict = utils._get_sg_inq_dict(sg_inq_output)
        self.assertEqual(output_dict['status'], 'online')
        self.assertEqual(output_dict['vendor'], 'IBM')
        self.assertEqual(output_dict['product'], '2145')
        self.assertEqual(output_dict['type'], 'disk')
        self.assertEqual(output_dict['controllerSN'], '0200a0435412XX00')

    def test_sg_luns_output(self):
        sg_luns_output = """Lun list length = 32 which imples 4 lun entries
Report luns [select_report=0x0]:
    0000000000000000
    0001000000000000
    0002000000000000
    0003000000000000
"""

        output_list = utils.parse_sg_luns(sg_luns_output)
        self.assertEqual(output_list[0], '0x0000000000000000')
        self.assertEqual(output_list[1], '0x0001000000000000')
        self.assertEqual(output_list[2], '0x0002000000000000')
        self.assertEqual(output_list[3], '0x0003000000000000')

    def test_validate_lun_path(self):
        lun_path = "0.0.3080:0x2005000e1115a1ef:0x0000000000000000"
        utils.validate_lun_path(lun_path)
        lun_path = "This is not really a LUN path, is it?"
        self.assertRaises(InvalidParameter, utils.validate_lun_path, lun_path)

    def test_validate_hba_id(self):
        hba_id = '0.0.3080'
        utils.validate_hba_id(hba_id)
        hba_id = 'Anything but HBA ID'
        self.assertRaises(InvalidParameter, utils.validate_hba_id, hba_id)

    def test_validate_wwpn_or_lun(self):
        wwpn = '0x2005000e1115a1ef'
        utils.validate_wwpn_or_lun(wwpn)

        lun_id = '0x0000000000000000'
        utils.validate_wwpn_or_lun(lun_id)

        invalid_id = "To be or not to be"
        self.assertRaises(
            InvalidParameter,
            utils.validate_wwpn_or_lun,
            invalid_id
        )

    def test_lun_scan(self):
        self.assertRaises(Exception, utils.enable_lun_scan, "2")

    def test_modify_boot_param(self):
        boot_params_str = """elevator=deadline crashkernel=196M \
zfcp.no_auto_port_rescan=1 zfcp.allow_lun_scan=0 cmma=on pci=on \
root=/dev/disk/by-path/ccw-0.0.5184-part1 rd_DASD=0.0.5184"""

        boot_param = "zfcp.allow_lun_scan"
        param_value = "1"

        boot_params_str = utils.modify_boot_param(
            boot_params_str, boot_param, param_value)
        pattern = r'.+zfcp\.allow_lun_scan=(\d)'
        m = re.search(pattern, boot_params_str)
        self.assertTrue(int(m.group(1)))
