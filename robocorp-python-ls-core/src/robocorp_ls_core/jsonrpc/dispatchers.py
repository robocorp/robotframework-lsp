# Original work Copyright 2018 Palantir Technologies, Inc. (MIT)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import functools
import re
from robocorp_ls_core.protocols import Sentinel

_RE_FIRST_CAP = re.compile("(.)([A-Z][a-z]+)")
_RE_ALL_CAP = re.compile("([a-z0-9])([A-Z])")


class MethodDispatcher(object):
    """JSON RPC dispatcher that calls methods on itself.

    Method names are computed by converting camel case to snake case, slashes with double underscores, and removing
    dollar signs.
    """

    def __getitem__(self, item):
        try:
            cache = self.__method_dispatcher_cache__
        except AttributeError:
            cache = self.__method_dispatcher_cache__ = {}

        handler = cache.get(item)
        if handler is None:

            method_name = f"m_{_method_to_string(item)}"
            if not hasattr(self, method_name):
                handler = Sentinel
            else:
                method = getattr(self, method_name)

                @functools.wraps(method)
                def _handler(params):
                    return method(**(params or {}))

                handler = _handler

            cache[item] = handler

        if handler is Sentinel:
            raise KeyError()
        return handler


def _method_to_string(method):
    return _camel_to_underscore(method.replace("/", "__").replace("$", ""))


def _camel_to_underscore(string):
    s1 = _RE_FIRST_CAP.sub(r"\1_\2", string)
    return _RE_ALL_CAP.sub(r"\1_\2", s1).lower()
