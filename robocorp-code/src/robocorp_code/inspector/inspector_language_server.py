import weakref
from pathlib import Path

from robocorp_ls_core.protocols import ActionResultDict
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class InspectorLanguageServer:
    def __init__(self):
        from robocorp_code.inspector.inspector_server_manager import (
            InspectorServerManager,
        )

        self._inspector_server_manager = InspectorServerManager(weakref.ref(self))

    # webInspectorCloseBrowser -> m_web_inspector_close_browser

    # webInspectorStartPicking
    def m_web_inspector_start_picking(self, **params):

        # send locator from picking to webview
        pass


    def m_web_inspector_close_browser(self, **params):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message("closeBrowser", {})

    def m_load_robot_locator_contents(self, directory: str) -> ActionResultDict:
        import json

        ret: ActionResultDict

        locators_json = Path(directory) / "locators.json"
        try:
            if locators_json.exists():
                with locators_json.open("rb") as stream:
                    contents = json.load(stream)
                    if isinstance(contents, dict):
                        ret = {
                            "success": True,
                            "message": None,
                            "result": contents,
                        }
                        return ret
                    else:
                        ret = {
                            "success": False,
                            "message": f"Expected locators.json to contain a dict. Found: {type(contents)}",
                            "result": {},
                        }
                        return ret
            else:
                # It does not exist. That's Ok (not really an error).
                ret = {
                    "success": True,
                    "message": None,
                    "result": {},
                }
                return ret
        except Exception as e:
            log.exception("Error loading locators.")
            ret = {
                "success": False,
                "message": f"There was an error loading locators. Error: {e}.",
                "result": {},
            }
            return ret

    def m_web_inspector_open_browser(self, url=None):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        if url is None:
            from robocorp_ls_core import uris

            from robocorp_code.inspector.web import INSPECTOR_GUIDE_PATH

            url = uris.from_fs_path(str(INSPECTOR_GUIDE_PATH))

        inspector_api_client.open_browser(url, wait=True)

    def m_web_inspector_click(self, locator):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.click(locator, wait=True)

    def m_web_inspector_start_pick(self, **params):
        from robocorp_ls_core import uris

        from robocorp_code.inspector.web import INSPECTOR_GUIDE_PATH

        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        url = uris.from_fs_path(str(INSPECTOR_GUIDE_PATH))
        inspector_api_client.send_sync_message(
            "startPick", {"url_if_new": url, "wait": True}
        )
