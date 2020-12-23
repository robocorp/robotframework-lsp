from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.protocols import IConfig
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_code.protocols import ActionResultDict

log = get_logger(__name__)


class LocatorServerApi(PythonLanguageServer):
    def __init__(self, read_from, write_to):
        from typing import Optional
        from robocorp_code.locators.locator_webdriver import Webdriver

        PythonLanguageServer.__init__(self, read_from, write_to)
        self._webdriver: Optional[Webdriver] = None

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robocorp_ls_core.config import Config

        return Config()

    def m_browser_locator__start(self, headless=False) -> ActionResultDict:
        try:
            from robocorp_code.locators.locator_webdriver import Webdriver

            w = self._webdriver
            if w:
                # If it's running, stop/restart it.
                self.m_browser_locator__stop()

            w = Webdriver(get_logger=get_logger, headless=headless)
            self._webdriver = w
            w.start()
            w.navigate("http://google.com")

            return {"success": True, "message": None, "result": True}
        except Exception as e:
            log.exception()
            return {"success": False, "message": str(e), "result": None}

    def m_image_locator__pick(self) -> ActionResultDict:
        try:
            from pathlib import Path
            from robocorp_code.locators.locator_protocols import ImageLocatorTypedDict
            from subprocess import CalledProcessError
            import json
            import subprocess
            import sys

            _region, value, source = json.loads(
                subprocess.check_output(
                    [
                        sys.executable,
                        str(Path(__file__).parent.parent / "locator_image.py"),
                    ],
                    stderr=subprocess.PIPE,
                )
            )
            result: ImageLocatorTypedDict = {
                "type": "image",
                "path_b64": value,
                "source_b64": source,
                "confidence": 80.0,
            }

            return {"success": True, "message": None, "result": result}
        except CalledProcessError as e:
            msg = f"Error on image locator.\nOutput:\n {e.output}\n\nStderr: {e.stderr}\n\nMessage: {str(e)}"
            log.exception(msg)
            return {"success": False, "message": msg, "result": None}

        except Exception as e:
            log.exception("Error on image locator")
            return {"success": False, "message": str(e), "result": None}

    def m_browser_locator__pick(self) -> ActionResultDict:
        try:
            w = self._webdriver
            if not w or not w.is_running:
                # If not running when pick is requested, start it now.
                self.m_browser_locator__start()

                w = self._webdriver
                if not w or not w.is_running:
                    return {
                        "success": False,
                        "message": "Browser for locator creation is not running.",
                        "result": None,
                    }

            result = w.pick_as_browser_locator_dict()

            return {"success": True, "message": None, "result": result}
        except Exception as e:
            log.exception()
            return {"success": False, "message": str(e), "result": None}

    def m_browser_locator__stop(self) -> ActionResultDict:
        try:
            w = self._webdriver
            if w:
                try:
                    w.stop()
                except Exception:
                    log.exception("Error handled stopping Webdriver")
                self._webdriver = None

            return {"success": True, "message": None, "result": True}
        except Exception as e:
            log.exception()
            return {"success": False, "message": str(e), "result": None}
