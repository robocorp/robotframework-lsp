import threading
import typing
from typing import Any, Callable, Optional, List

from robocorp_ls_core.protocols import IEndPoint
from robocorp_ls_core.callbacks import Callback
from robocorp_ls_core.robotframework_log import get_logger

from ._bridge import ImageBridge

log = get_logger(__name__)


class _PickerThread(threading.Thread):
    def __init__(
        self,
        bridge: Optional[ImageBridge],
        confidence: Optional[int],
        on_pick,
    ) -> None:
        threading.Thread.__init__(self)

        self._stop_event = threading.Event()
        self.bridge = bridge
        self.on_pick = on_pick
        self.confidence = confidence

    def run(self) -> None:
        try:
            self._run()
        except Exception as e:
            log.exception("Exception occurred:", e)

    def _run(self) -> None:
        assert self.bridge is not None

        result_dict = self.bridge.pick(confidence=self.confidence)
        self.on_pick(result_dict)


class _ValidateThread(threading.Thread):
    def __init__(
        self,
        bridge: Optional[ImageBridge],
        image_base64: str,
        confidence: Optional[int],
        on_validate,
    ) -> None:
        threading.Thread.__init__(self)

        self._stop_event = threading.Event()
        self.bridge = bridge
        self.image_base64 = image_base64
        self.confidence = confidence
        self.on_validate = on_validate

    def run(self) -> None:
        try:
            self._run()
        except Exception as e:
            log.exception("Exception occurred:", e)

    def _run(self) -> None:
        assert self.bridge is not None

        matches = self.bridge.validate(
            image_base64=self.image_base64, confidence=self.confidence
        )
        self.on_validate(matches)


class IOnPickCallback(typing.Protocol):
    def __call__(self, locator_info_tree: List[dict]):
        pass

    def register(self, callback: Callable[[Any], Any]) -> None:
        pass

    def unregister(self, callback: Callable[[Any], Any]) -> None:
        pass


class ImageInspector:
    def __init__(self, endpoint: Optional[IEndPoint] = None) -> None:
        """
        Args:
            endpoint: If given notifications on the state will be given.
        """
        # callbacks
        self.on_pick: IOnPickCallback = Callback()
        self.on_validate: IOnPickCallback = Callback()
        # internals
        self._image_bridge = ImageBridge(endpoint=endpoint, logger=log)
        # threads
        self._current_thread = threading.current_thread()
        self._picker_thread: Optional[_PickerThread] = None
        self._validate_thread: Optional[_ValidateThread] = None

    def _check_thread(self):
        assert self._current_thread is threading.current_thread()

    def start_pick(self, confidence: Optional[int] = None) -> None:
        self._check_thread()
        log.debug("Image:: Start pick...")

        self._picker_thread = _PickerThread(
            bridge=self._image_bridge,
            confidence=confidence,
            on_pick=self.on_pick,
        )
        self._picker_thread.start()

    def stop_pick(self) -> None:
        self._check_thread()
        log.debug("Image:: Stop pick...")
        if self._picker_thread:
            self._picker_thread._stop_event.set()
        if self._validate_thread:
            self._validate_thread._stop_event.set()
        self._image_bridge.stop()

    # TODO: replace this implementation when the robocorp library has image recognition
    def validate(self, image_base64: str, confidence: Optional[int] = None) -> None:
        self._check_thread()
        log.debug("Image:: Validate pick...")

        self._validate_thread = _ValidateThread(
            bridge=self._image_bridge,
            image_base64=image_base64,
            confidence=confidence,
            on_validate=self.on_validate,
        )
        self._validate_thread.start()

    def save_image(self, root_directory: str, image_base64: str) -> str:
        self._check_thread()
        log.debug("Image:: Save image...")
        return self._image_bridge.save_image(
            root_directory=root_directory, image_base64=image_base64
        )

    def shutdown(self):
        if self._image_bridge:
            self._image_bridge.stop()
        if self._picker_thread:
            self._picker_thread._stop_event.set()
        if self._validate_thread:
            self._validate_thread._stop_event.set()
