import weakref


class InspectorLanguageServer:
    def __init__(self):
        from robocorp_code.inspector.inspector_server_manager import (
            InspectorServerManager,
        )

        self._inspector_server_manager = InspectorServerManager(weakref.ref(self))

    def m_web_inspector_close_browser(self, **params):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message("closeBrowser", {})

    def m_web_inspector_open_browser(self, **params):
        from robocorp_ls_core import uris

        from robocorp_code.inspector.web import INSPECTOR_GUIDE_PATH

        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        url = uris.from_fs_path(str(INSPECTOR_GUIDE_PATH))
        inspector_api_client.send_sync_message(
            "openBrowser", {"url": url, "wait": True}
        )

    def m_web_inspector_pick(self, **params):
        from robocorp_ls_core import uris

        from robocorp_code.inspector.web import INSPECTOR_GUIDE_PATH

        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        url = uris.from_fs_path(str(INSPECTOR_GUIDE_PATH))
        inspector_api_client.send_sync_message(
            "startPick", {"url_if_new": url, "wait": True}
        )
