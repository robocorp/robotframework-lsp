# Original work Copyright 2017 Palantir Technologies, Inc. (MIT)
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
from robocode_ls_core import uris
from robocode_ls_core.robotframework_log import get_logger
from robocode_ls_core.basic import implements
from robocode_ls_core.protocols import IConfig, Sentinel
from typing import Any, Dict, Optional


log = get_logger(__name__)


class Config(object):
    def __init__(
        self,
        root_uri: str,
        init_opts: Optional[Dict] = None,
        process_id: Optional[int] = None,
        capabilities: Optional[Dict] = None,
    ):
        self._root_path = uris.to_fs_path(root_uri)
        self._root_uri = root_uri
        self._init_opts = init_opts
        self._process_id = process_id
        self._capabilities = capabilities

        self._settings: Dict = {}

    @property
    def init_opts(self):
        return self._init_opts

    @property
    def root_uri(self):
        return self._root_uri

    @property
    def process_id(self):
        return self._process_id

    @property
    def capabilities(self):
        return self._capabilities

    @implements(IConfig.get_setting)
    def get_setting(self, key, expected_type, default=Sentinel.SENTINEL) -> Any:
        try:
            s = self._settings
            for part in key.split("."):
                s = s[part]

            if not isinstance(s, expected_type):
                try:
                    # Check if we can cast it...
                    s = expected_type(s)
                except:
                    raise KeyError(
                        "Expected %s to be a setting of type: %s. Found: %s"
                        % (key, expected_type, type(s))
                    )
        except KeyError:
            if default is not Sentinel.SENTINEL:
                return default
            raise
        return s

    @implements(IConfig.update)
    def update(self, settings):
        self._settings = settings
        log.info("Updated settings to %s", self._settings)

    def get_internal_settings(self):
        return self._settings
