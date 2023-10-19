import weakref
from pathlib import Path

from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class InspectorLanguageServer:
    def __init__(self):
        from robocorp_code.inspector.inspector_server_manager import (
            InspectorServerManager,
        )

        self._inspector_server_manager = InspectorServerManager(weakref.ref(self))

    def get_locators_json_path(self, directory: str) -> str:
        return Path(directory) / "locators.json"

    def m_web_inspector_close_browser(self, **params) -> dict:
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message("closeBrowser", {})

    def m_load_robot_locator_contents(self, message: dict, directory: str) -> dict:
        import json

        locators_json = self.get_locators_json_path(directory)
        try:
            if locators_json.exists():
                with locators_json.open("rb") as stream:
                    contents = json.load(stream)
                    if isinstance(contents, dict):
                        ret = {
                            "id": message["id"],
                            "type": "response",
                            "app": message["app"],
                            "status": "success",
                            "message": None,
                            "data": contents,
                            "dataType": "locatorsMap",
                        }
                        return ret
                    else:
                        ret = {
                            "id": message["id"],
                            "type": "response",
                            "app": message["app"],
                            "status": "failure",
                            "message": f"Expected locators.json to contain a dict. Found: {type(contents)}",
                            "data": {},
                            "dataType": "locatorsMap",
                        }
                        return ret
            else:
                # It does not exist. That's Ok (not really an error).
                ret = {
                    "id": message["id"],
                    "type": "response",
                    "app": message["app"],
                    "status": "success",
                    "message": None,
                    "data": {},
                    "dataType": "locatorsMap",
                }
                return ret
        except Exception as e:
            log.exception("Error loading locators.")
            ret = {
                "id": message["id"],
                "type": "response",
                "app": message["app"],
                "status": "failure",
                "message": None,
                "data": {},
                "dataType": "locatorsMap",
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

    def m_web_inspector_stop_pick(self, **params):
        inspector_api_client = self._inspector_server_manager.get_inspector_api_client()
        inspector_api_client.send_sync_message("stopPick", {"wait": True})

    def m_web_inspector_save_locator(
        self,
        message: dict,
        directory: str,
    ):
        import json

        log.info(f"Received params: [dir]:{directory} [message]:{message}")
        locator = message["command"]["locator"]
        locators_event = self.m_load_robot_locator_contents(
            message=message, directory=directory
        )
        log.info(f"Locators result: {locators_event}")
        if locators_event["status"] == "success" and "name" in locator:
            locators = locators_event["data"]
            new_name = locator["name"]
            log.info(f"New Locator name: {new_name}")
            if new_name:
                log.info(f"The internal locators: {locators}")

                locators[new_name] = locator
                log.info(f"Will update locator: {new_name}")

                locators_json = self.get_locators_json_path(directory)
                with locators_json.open("w") as file:
                    file.write(json.dumps(locators, indent=4))
                log.info(f"Saved locators into file!")
                return {
                    "id": message["id"],
                    "app": message["app"],
                    "type": "response",
                    "status": "success",
                    "message": None,
                }
        log.info(f"Name doesn't exist or couldn't find the locator!")
        return {
            "id": message["id"],
            "app": message["app"],
            "type": "response",
            "status": "failure",
            "message": "Name doesn't exist or couldn't find the locator!",
        }
