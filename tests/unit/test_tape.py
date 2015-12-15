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

from model import utils


class TapeDevTests(unittest.TestCase):
    """
    unit tests for Tape devices
    """
    @mock.patch('model.utils.get_tape_uuid')
    def test_lstape_parser(self, mock_uuid):
        mock_uuid.return_value = 'sdfsdfdssfsdf'
        output = """Generic Device        Target       Vendor   Model            Type     State
sg3     st0           1:0:2:0      IBM      ULT3580-HH6      tapedrv  running
sg3     st0           1:0:2:0      IBM      ULT3580-HH6      tapedrv  running
sg3     st0           1:0:2:0      IBM      ULT3580-HH6      tapedrv  running
"""

        final_list = utils.parse_tape_list(output)
        self.assertEqual(len(final_list), 3)
        self.assertEqual(final_list[0]['Generic'], 'sg3')
        self.assertEqual(final_list[0]['Target'], '1:0:2:0')
