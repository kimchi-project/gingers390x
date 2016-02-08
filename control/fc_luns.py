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

from wok.control.base import Collection, Resource
from wok.control.utils import UrlSubNode


@UrlSubNode("lunscan")
class LUNScan(Resource):
    """
    Resource representing the status of LUN scanning
    """

    def __init__(self, model):
        super(LUNScan, self).__init__(model)
        self.admin_methods = ['GET', 'POST']
        self.role_key = "administration"
        self.uri_fmt = "/lunscan/%s"
        self.enable = self.generate_action_handler_task('enable')
        self.disable = self.generate_action_handler_task('disable')
        self.trigger = self.generate_action_handler_task('trigger')

    @property
    def data(self):
        return self.info


@UrlSubNode("fcluns")
class FCLUNs(Collection):
    """
    Collections representing the FC LUNs on the system
    """

    def __init__(self, model):
        super(FCLUNs, self).__init__(model)
        self.role_key = 'host'
        self.admin_methods = ['GET', 'POST', 'DELETE']
        self.resource = FCLUN


class FCLUN(Resource):
    """
    Resource representing a single LUN
    """

    def __init__(self, model, ident):
        super(FCLUN, self).__init__(model, ident)
        self.role_key = 'host'
        self.admin_methods = ['GET', 'POST', 'DELETE']
        self.uri_fmt = "/fcluns/%s"

    @property
    def data(self):
        return self.info
