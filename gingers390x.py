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

import json
import os

from wok.root import WokRoot

from wok.plugins.gingers390x import config, mockmodel
from wok.plugins.gingers390x.i18n import messages
from wok.plugins.gingers390x.control import sub_nodes
from wok.plugins.gingers390x.model import model as gingerS390xModel


class GingerS390x(WokRoot):
    def __init__(self, wok_options):
        if hasattr(wok_options, "model"):
            self.model = wok_options.model
        elif wok_options.test:
            self.model = mockmodel.MockModel()
        else:
            self.model = gingerS390xModel.Model()

        dev_env = wok_options.environment != 'production'
        super(GingerS390x, self).__init__(self.model, dev_env)

        for ident, node in sub_nodes.items():
            setattr(self, ident, node(self.model))

        self.api_schema = json.load(open(os.path.join(os.path.dirname(
                                    os.path.abspath(__file__)), 'API.json')))
        self.paths = config.gingerS390xPaths
        self.domain = 'gingers390x'
        self.messages = messages

        make_dirs = [
            os.path.dirname(os.path.abspath(config.get_object_store())),
        ]
        for directory in make_dirs:
            if not os.path.isdir(directory):
                os.makedirs(directory)

    def get_custom_conf(self):
        return config.GingerS390xConfig()
