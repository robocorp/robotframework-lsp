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
from typing import Any, FrozenSet, Optional
import os


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

        self._original_settings: dict = {}
        self._original_override_settings: dict = {}

        self._full_settings: dict = {}
        self._workspace_dir: Optional[str] = None

    @implements(IConfig.get_setting)
    def get_setting(self, key, expected_type, default=Sentinel.SENTINEL) -> Any:
        try:
            s = self._full_settings[key]
            if not isinstance(s, expected_type):
                if isinstance(expected_type, tuple):
                    # Don't try to make a cast if a tuple of classes was passed.
                    if default is not Sentinel.SENTINEL:
                        return default

                    raise KeyError(
                        "Expected %s to be a setting of type: %s. Found: %s"
                        % (key, expected_type, type(s))
                    )

                try:
                    if expected_type in (list, tuple):
                        if expected_type == list and isinstance(s, tuple):
                            return expected_type(s)

                        if expected_type == tuple and isinstance(s, list):
                            return expected_type(s)

                        # Don't try to make a cast for list or tuple (we don't
                        # want a string to end up being a list of chars).
                        if default is not Sentinel.SENTINEL:
                            return default

                        raise KeyError(
                            "Expected %s to be a setting of type: %s. Found: %s"
                            % (key, expected_type, type(s))
                        )

                    # Check if we can cast it...
                    return expected_type(s)
                except:
                    if default is not Sentinel.SENTINEL:
                        return default

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
        log.debug("Updated settings to %s", full_settings)

    def _get_var_value(self, name):
        ret = name
        if name in ("${workspace}", "${workspaceRoot}", "${workspaceFolder}"):
            if self._workspace_dir is not None:
                ret = self._workspace_dir
            else:
                log.info("Unable to make workspace replacement for variable: %s", name)

        elif (name.startswith("${env.") or name.startswith("${env:")) and name.endswith(
            "}"
        ):
            name = name[6:-1]
            ret = os.environ.get(name)  # Note: should be case-insensitive on windows.
        else:
            log.info("Unable to resolve variable: %s", name)

        return ret

    def _var_replace(self, option, value):
        import re

        compiled = re.compile(r"\${([^{}]*)}")
        lasti = 0
        new_value = []
        for o in compiled.finditer(value):
            new_value.append(value[lasti : o.start()])
            new_value.append(self._get_var_value(o.group(0)))
            lasti = o.end()

        if lasti == 0:
            # Nothing changed
            return value

        new_value.append(value[lasti:])
        ret = "".join(new_value)
        if ret.startswith("~"):
            ret = os.path.expanduser(ret)

        log.debug("Changed setting: %s from %s to %s", option, value, ret)

        return ret

    def _replace_variables_in_settings(self, settings: dict) -> dict:
        """
        :param settings:
            The settings where the variables should be replaced.
            Note that this instance is unchanged.

        :return dict:
            Returns a new dict with the variables replaced.
        """
        settings = settings.copy()
        for option in self.ALL_OPTIONS:
            value = settings.get(option)
            if isinstance(value, str):
                settings[option] = self._var_replace(option, value)

            elif isinstance(value, list):
                new_value = []
                for val in value:
                    if isinstance(val, str):
                        new_value.append(self._var_replace(option, val))
                    else:
                        new_value.append(val)
                settings[option] = new_value

            elif isinstance(value, dict):
                new_dct = {}
                for key, val in value.items():
                    if isinstance(val, str):
                        new_dct[key] = self._var_replace(option, val)
                    else:
                        new_dct[key] = val
                settings[option] = new_dct
        return settings

    @implements(IConfig.update)
    def update(self, settings: dict):
        settings = flatten_keys(settings, all_options=self.ALL_OPTIONS)
        self._original_settings = settings
        self._settings = self._replace_variables_in_settings(settings)
        self._update_full_settings()

    @implements(IConfig.set_override_settings)
    def set_override_settings(self, override_settings):
        settings = flatten_keys(override_settings, all_options=self.ALL_OPTIONS)
        self._original_override_settings = settings
        self._override_settings = self._replace_variables_in_settings(settings)
        self._update_full_settings()

    @implements(IConfig.update_override_settings)
    def update_override_settings(self, override_settings):
        settings = flatten_keys(override_settings, all_options=self.ALL_OPTIONS)
        original = self._original_override_settings.copy()
        original.update(settings)

        self._original_override_settings = original
        self._override_settings = self._replace_variables_in_settings(original)
        self._update_full_settings()

    @implements(IConfig.get_full_settings)
    def get_full_settings(self):
        return self._full_settings

    @implements(IConfig.set_workspace_dir)
    def set_workspace_dir(self, workspace: str):
        self._workspace_dir = workspace
        self._settings = self._replace_variables_in_settings(self._original_settings)
        self._override_settings = self._replace_variables_in_settings(
            self._original_override_settings
        )
        self._update_full_settings()
