# Copyright 2017 Palantir Technologies, Inc.
# License: MIT
import logging

try:
    from functools import lru_cache
except ImportError:
    from py2_backports.functools_lru_cache import lru_cache


from robotframework_ls import _utils, uris

log = logging.getLogger(__name__)


class Config(object):
    def __init__(self, root_uri, init_opts, process_id, capabilities):
        self._root_path = uris.to_fs_path(root_uri)
        self._root_uri = root_uri
        self._init_opts = init_opts
        self._process_id = process_id
        self._capabilities = capabilities

        self._settings = {}
        self._plugin_settings = {}

        self._config_sources = {}

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

    @lru_cache(maxsize=32)
    def settings(self, document_path=None):
        """Settings are constructed from a few sources:

            1. User settings, found in user's home directory
            2. Plugin settings, reported by PyLS plugins
            3. LSP settings, given to us from didChangeConfiguration
            4. Project settings, found in config files in the current project.

        Since this function is nondeterministic, it is important to call
        settings.cache_clear() when the config is updated
        """
        settings = {}
        sources = self._settings.get("configurationSources", [])

        for source_name in reversed(sources):
            source = self._config_sources.get(source_name)
            if not source:
                continue
            source_conf = source.user_config()
            log.debug(
                "Got user config from %s: %s", source.__class__.__name__, source_conf
            )
            settings = _utils.merge_dicts(settings, source_conf)
        log.debug("With user configuration: %s", settings)

        settings = _utils.merge_dicts(settings, self._plugin_settings)
        log.debug("With plugin configuration: %s", settings)

        settings = _utils.merge_dicts(settings, self._settings)
        log.debug("With lsp configuration: %s", settings)

        for source_name in reversed(sources):
            source = self._config_sources.get(source_name)
            if not source:
                continue
            source_conf = source.project_config(document_path or self._root_path)
            log.debug(
                "Got project config from %s: %s", source.__class__.__name__, source_conf
            )
            settings = _utils.merge_dicts(settings, source_conf)
        log.debug("With project configuration: %s", settings)

        return settings

    def find_parents(self, path, names):
        root_path = uris.to_fs_path(self._root_uri)
        return _utils.find_parents(root_path, path, names)

    def plugin_settings(self, plugin, document_path=None):
        return (
            self.settings(document_path=document_path)
            .get("plugins", {})
            .get(plugin, {})
        )

    def update(self, settings):
        """Recursively merge the given settings into the current settings."""
        self.settings.cache_clear()
        self._settings = settings
        log.info("Updated settings to %s", self._settings)
