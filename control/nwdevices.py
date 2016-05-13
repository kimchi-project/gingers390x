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
from wok.control.utils import model_fn, UrlSubNode


NWDEVICE_REQUESTS = {
    'POST': {
        'configure': "GS390XIONW0001L",
        'unconfigure': "GS390XIONW0002L",
    }
}


@UrlSubNode('nwdevices', True)
class NetworkDevices(Collection):
    def __init__(self, model):
        super(NetworkDevices, self).__init__(model)
        self.role_key = 'administration'
        self.admin_methods = ['GET']
        self.resource = NetworkDevice

    def _get_resources(self, flag_filter):
        try:
            get_list = getattr(self.model, model_fn(self, 'get_list'))
            idents = get_list(*self.model_args, **flag_filter)
            res_list = []
            for ident in idents:
                args = self.resource_args + [ident]
                res = self.resource(self.model, *args)
                res.info = ident
                res_list.append(res)
            return res_list
        except AttributeError:
            return []


class NetworkDevice(Resource):
    """
    Network device resource
    """
    def __init__(self, model, ident):
        super(NetworkDevice, self).__init__(model, ident)
        self.role_key = "administration"
        self.admin_methods = ['GET', 'POST']
        self.uri_fmt = '/nwdevices/%s'
        self.configure = self.generate_action_handler_task('configure')
        self.unconfigure = self.generate_action_handler_task('unconfigure')
        self.log_map = NWDEVICE_REQUESTS

    @property
    def data(self):
        return self.info
