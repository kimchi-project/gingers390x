#
# Project Ginger S390x
#
# Copyright IBM Corp, 2015-2016
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

EXTRA_DIST = theme-default

cssdir = $(datadir)/wok/plugins/gingers390x/ui/css
dist_css_DATA = bootgrid.css gingers390x.css

%.css: src/%.scss
	echo "Compiling .scss file $<"
	sassc -s expanded $< $(@:.scss=.css)

CLEANFILES = bootgrid.css gingers390x.css
