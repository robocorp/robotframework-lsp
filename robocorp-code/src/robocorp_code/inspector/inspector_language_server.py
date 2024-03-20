import weakref
from functools import partial
from pathlib import Path
from typing import Literal, Optional

from robocorp_ls_core.protocols import ActionResultDict
from robocorp_ls_core.robotframework_log import get_logger


log = get_logger(__name__)


class InspectorLanguageServer:
    def __init__(self):
        from robocorp_code.inspector.inspector_server_manager import (
            InspectorServerManager,
        )

        self._inspector_server_manager = InspectorServerManager(weakref.ref(self))

    def get_locators_json_path(self, directory: str) -> Path:
        return Path(directory) / "locators.json"

    def m_kill_inspectors(self, inspector: Optional[str]) -> None:
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message(
            "killInspectors", dict(inspector=inspector)
        )

    def m_manager_save_locator(
        self,
        locator: dict,
        directory: str,
    ) -> ActionResultDict:
        import json

        ret: ActionResultDict

        if not locator:
            ret = {
                "success": False,
                "message": f"Error: no locator information passed.",
                "result": None,
            }
            return ret

        name = str(locator.get("name", "")).strip()
        if not name:
            ret = {
                "success": False,
                "message": f"Error: the locator passed {locator} does not have a name (or the name is invalid).",
                "result": None,
            }
            return ret
        # Use the stripped version.
        locator["name"] = name

        loaded_locators_action_result = self.m_manager_load_locators(
            directory=directory
        )

        if not loaded_locators_action_result["success"]:
            # TODO: We should have a way of forcing this to override even if
            # the current version is not correct.
            ret = {
                "success": False,
                "message": f'The locator was not saved because there was an issue loading the existing locators: {loaded_locators_action_result["message"]}',
                "result": None,
            }
            return ret
        locators = loaded_locators_action_result["result"]

        locators[name] = locator

        locators_json = self.get_locators_json_path(directory)
        try:
            with locators_json.open("w") as file:
                file.write(json.dumps(locators, indent=4))
        except Exception as e:
            log.exception("Error saving locators")
            ret = {
                "success": False,
                "message": f"Error happened while saving locator: {e}.",
                "result": None,
            }
            return ret
        ret = {
            "success": True,
            "message": "",
            "result": None,
        }
        return ret

    def m_manager_delete_locators(
        self,
        directory: str,
        ids: list[str],
    ) -> ActionResultDict:
        ret: ActionResultDict

        if not ids:
            ret = {
                "success": False,
                "message": f"Error: no ids specified for deleting.",
                "result": None,
            }
            return ret

        import json

        loaded_locators_action_result = self.m_manager_load_locators(
            directory=directory
        )
        if not loaded_locators_action_result["success"]:
            ret = {
                "success": False,
                "message": f'The locators were not deleted because there was an issue loading the existing locators: {loaded_locators_action_result["message"]}',
                "result": None,
            }
            return ret

        locators = loaded_locators_action_result["result"]
        for locator_id in ids:
            locators.pop(locator_id, None)

        locators_json = self.get_locators_json_path(directory)
        try:
            with locators_json.open("w") as file:
                file.write(json.dumps(locators, indent=4))
        except Exception as e:
            log.exception("Error saving locators")
            ret = {
                "success": False,
                "message": f"Error happened while deleting locators: {e}.",
                "result": None,
            }
            return ret
        ret = {
            "success": True,
            "message": "",
            "result": None,
        }
        return ret

    def m_manager_load_locators(self, directory: str) -> ActionResultDict:
        import json

        ret: ActionResultDict

        locators_json = self.get_locators_json_path(directory)
        try:
            if locators_json.exists():
                with locators_json.open("rb") as stream:
                    file_contents = stream.read()
                    if not file_contents.strip():
                        # Ok, an empty file is valid.
                        ret = {
                            "success": True,
                            "message": None,
                            "result": {},
                        }
                        return ret

                contents = json.loads(file_contents)

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

    def m_web_inspector_configure_browser(
        self, width: int = 1280, height: int = 720, url: str = ""
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message(
            "browserConfigure",
            {"viewport_size": (width, height), "url": url},
        )

    def m_web_inspector_open_browser(self, url=None):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        if url is None:
            from robocorp_ls_core import uris

            from robocorp_code.inspector.web import INSPECTOR_GUIDE_PATH

            url = uris.from_fs_path(str(INSPECTOR_GUIDE_PATH))

        inspector_api_client.send_sync_message("openBrowser", dict(url=url, wait=True))

    def m_web_inspector_close_browser(self, **params) -> None:
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message("closeBrowser", {})

    def m_web_inspector_click(self, locator):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message(
            "click", dict(locator=locator, wait=True)
        )

    def m_web_inspector_start_pick(self, **params):
        from robocorp_ls_core import uris

        from robocorp_code.inspector.web import INSPECTOR_GUIDE_PATH

        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        url = (
            params["url_if_new"]
            if params and "url_if_new" in params
            else uris.from_fs_path(str(INSPECTOR_GUIDE_PATH))
        )
        inspector_api_client.send_sync_message(
            "startPick", {"url_if_new": url, "wait": True}
        )

    def m_web_inspector_stop_pick(self, **params):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message("stopPick", {"wait": True})

    def m_web_inspector_validate_locator(self, **params):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        return partial(
            inspector_api_client.send_sync_message,
            "validateLocator",
            {"locator": params["locator"], "url": params["url"], "wait": True},
        )

    def m_windows_inspector_parse_locator(self, locator: str):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsParseLocator",
            {"locator": locator},
        )

    def m_windows_inspector_set_window_locator(self, locator: str):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsSetWindowLocator",
            {"locator": locator},
        )

    def m_windows_inspector_list_windows(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsListWindows",
            {},
        )

    def m_windows_inspector_start_pick(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsStartPick",
            {},
        )

    def m_windows_inspector_stop_pick(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsStopPick",
            {},
        )

    def m_windows_inspector_start_highlight(
        self,
        locator: str,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsStartHighlight",
            dict(
                locator=locator,
                search_depth=search_depth,
                search_strategy=search_strategy,
            ),
        )

    def m_windows_inspector_collect_tree(
        self,
        locator: str,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsCollectTree",
            dict(
                locator=locator,
                search_depth=search_depth,
                search_strategy=search_strategy,
            ),
        )

    def m_windows_inspector_stop_highlight(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "windowsStopHighlight",
            {},
        )

    def m_image_inspector_start_pick(
        self, minimize: Optional[bool], confidence_level: Optional[int]
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        return partial(
            inspector_api_client.send_sync_message,
            "imageStartPick",
            {"minimize": minimize, "confidence_level": confidence_level},
        )

    def m_image_inspector_stop_pick(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        return partial(inspector_api_client.send_sync_message, "imageStopPick", {})

    def m_image_inspector_validate_locator(
        self, locator: dict, confidence_level: Optional[bool]
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        return partial(
            inspector_api_client.send_sync_message,
            "imageValidateLocator",
            {"locator": locator, "confidence_level": confidence_level},
        )

    def m_image_inspector_save_image(self, root_directory: str, image_base64: str):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        return partial(
            inspector_api_client.send_sync_message,
            "imageSaveImage",
            {"root_directory": root_directory, "image_base64": image_base64},
        )

    def m_java_inspector_parse_locator(self, locator: str):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaParseLocator",
            {"locator": locator},
        )

    def m_java_inspector_set_window_locator(self, locator: str):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaSetWindowLocator",
            {"locator": locator},
        )

    def m_java_inspector_list_windows(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaListWindows",
            {},
        )

    def m_java_inspector_start_pick(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaStartPick",
            {},
        )

    def m_java_inspector_stop_pick(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaStopPick",
            {},
        )

    def m_java_inspector_start_highlight(
        self,
        locator: str,
        search_depth: int = 8,
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaStartHighlight",
            dict(
                locator=locator,
                search_depth=search_depth,
            ),
        )

    def m_java_inspector_collect_tree(
        self,
        locator: str,
        search_depth: int = 8,
    ):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaCollectTree",
            dict(
                locator=locator,
                search_depth=search_depth,
            ),
        )

    def m_java_inspector_stop_highlight(self):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        # Not blocking (return callback to run in thread).
        return partial(
            inspector_api_client.send_sync_message,
            "javaStopHighlight",
            {},
        )
