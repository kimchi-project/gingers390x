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

from wok.control.base import Resource
from wok.control.utils import UrlSubNode

CIOIGNORE_REQUESTS = {
    'POST': {
        'remove': "GS390XIOIG0001L",
        }
}


@UrlSubNode("cio_ignore")
class CIOIgnore(Resource):
    def __init__(self, model):
        super(CIOIgnore, self).__init__(model)
        self.admin_methods = ['GET', 'POST']
        self.role_key = "administration"
        self.uri_fmt = "/cio_ignore/%s"
        self.params = ['devices']
        self.remove = self.generate_action_handler_task('remove', self.params)
        self.log_map = CIOIGNORE_REQUESTS

    @property
    def data(self):
        return self.info
