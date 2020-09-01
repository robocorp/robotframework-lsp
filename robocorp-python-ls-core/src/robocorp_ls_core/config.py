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
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import implements
from robocorp_ls_core.protocols import IConfig, Sentinel
from typing import Any, FrozenSet


log = get_logger(__name__)


def flatten_keys(d: dict, parent_key="", all_options=frozenset(), result_dict=None):
    if result_dict is None:
        result_dict = {}

    for k, v in d.items():
        new_key = parent_key + "." + k if parent_key else k

        if new_key not in all_options and isinstance(v, dict):
            flatten_keys(v, new_key, all_options, result_dict)
            continue

        result_dict[new_key] = v
    return result_dict


class Config(object):
    ALL_OPTIONS: FrozenSet[str] = frozenset()

    def __init__(self, all_options: FrozenSet[str] = frozenset()):
        if all_options:
            self.ALL_OPTIONS = all_options

        self._settings: dict = {}
        self._override_settings: dict = {}
        self._full_settings: dict = {}

    @implements(IConfig.get_setting)
    def get_setting(self, key, expected_type, default=Sentinel.SENTINEL) -> Any:
        try:
            s = self._full_settings[key]
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

    def _update_full_settings(self):
        full_settings = self._settings.copy()
        full_settings.update(self._override_settings)
        self._full_settings = full_settings
        log.info("Updated settings to %s", full_settings)

    @implements(IConfig.update)
    def update(self, settings: dict):
        settings = flatten_keys(settings, all_options=self.ALL_OPTIONS)
        self._settings = settings
        self._update_full_settings()

    @implements(IConfig.set_override_settings)
    def set_override_settings(self, override_settings):
        settings = flatten_keys(override_settings, all_options=self.ALL_OPTIONS)
        self._override_settings = settings
        self._update_full_settings()

    @implements(IConfig.get_full_settings)
    def get_full_settings(self):
        return self._full_settings
