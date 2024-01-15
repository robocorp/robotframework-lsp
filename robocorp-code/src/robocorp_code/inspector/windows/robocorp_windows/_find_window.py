import time
from typing import List, Literal, Optional, Tuple

from ._errors import ElementNotFound
from ._match_ast import OrSearchParams, SearchParams
from ._ui_automation_wrapper import _UIAutomationControlWrapper
from ._window_element import WindowElement
from .protocols import Locator


def restrict_to_window_locators(
    or_search_params: Tuple[OrSearchParams, ...],
) -> Tuple[OrSearchParams, ...]:
    last_part: OrSearchParams = or_search_params[-1]
    also_add_as_pane = []
    for search_params in last_part.parts:
        assert isinstance(search_params, SearchParams)

        # Ok, leave is is (the type is already defined)
        if search_params.search_params.get(
            "control", search_params.search_params.get("type")
        ):
            continue

        # Now, for each search param we have to add a new entry where we check
        # for both 'WindowControl' and 'PaneControl'
        also_add_as_pane.append(search_params.copy())
        search_params.search_params["type"] = "WindowControl"

    for param in also_add_as_pane:
        param.search_params["type"] = "PaneControl"
        last_part.parts.append(param)

    return or_search_params


def find_window(
    root_element: Optional[_UIAutomationControlWrapper],
    locator: Locator,
    search_depth: int = 1,
    timeout: Optional[float] = None,
    wait_time: Optional[float] = None,
    foreground: bool = True,
    move_cursor_to_center: bool = True,
) -> WindowElement:
    from . import config as windows_config
    from ._find_ui_automation import (
        LocatorStrAndOrSearchParams,
        find_ui_automation_wrapper,
    )
    from ._match_ast import collect_search_params

    config = windows_config()
    or_search_params = collect_search_params(locator)
    restrict_to_window_locators(or_search_params)

    locator_and_or_search_params = LocatorStrAndOrSearchParams(
        locator, or_search_params
    )

    if timeout is None:
        timeout = config.timeout

    assert timeout is not None
    if wait_time is None:
        wait_time = config.wait_time

    try:
        element = find_ui_automation_wrapper(
            locator_and_or_search_params,
            search_depth,
            root_element=root_element,
            timeout=timeout,
        )
        window_element = WindowElement(element)

        from robocorp_ls_core.robotframework_log import get_logger

        log = get_logger(__name__)

        log.info(">>>>> Trying to activate the legacy pattern!")

        try:
            import ctypes
            import comtypes
            from comtypes import IUnknown, GUID
            from comtypes.client import GetBestInterface, CreateObject

            # Define necessary structures and constants
            ACCESSIBLE_OBJECT_ID = 0xFFFFFFFC
            IID_IAccessible2 = GUID("{E89F726E-C4F4-4c19-BB19-B647D7FA8478}")

            # Define the necessary interfaces
            class IAccessible(IUnknown):
                _iid_ = GUID("{618736e0-3c3d-11cf-810c-00aa00389b71}")

            class IServiceProvider(IUnknown):
                _iid_ = GUID("{6d5140c1-7436-11ce-8034-00aa006009fa}")

            # Function to get IAccessible2 interface
            def get_IAccessible2(acc):
                try:
                    log.info(
                        ">>>>> get_IAccessible2 - Trying to get the interface from the service provider..."
                    )
                    service_provider = GetBestInterface(acc, IServiceProvider)
                    log.info(
                        ">>>>> get_IAccessible2 - Service provider:", service_provider
                    )
                    intf = GetBestInterface(service_provider, IID_IAccessible2)
                    log.info(">>>>> get_IAccessible2 - Interface:", intf)
                    return intf
                except Exception:
                    return None

            # Function to get IAccessible from window handle
            def get_IAccessible_from_window(hwnd):
                log.info(">>>>> get_IAccessible_from_window - hwnd:", hwnd)
                acc = CreateObject(
                    "{618736e0-3c3d-11cf-810c-00aa00389b71}", None, None, IAccessible
                )
                log.info(">>>>> get_IAccessible_from_window - acc object:", acc)
                ptr_acc_obj = ctypes.windll.oleacc.AccessibleObjectFromWindow(
                    hwnd,
                    ACCESSIBLE_OBJECT_ID,
                    ctypes.byref(IAccessible._iid_),
                    ctypes.byref(acc),
                )
                log.info(
                    ">>>>> get_IAccessible_from_window - ptr_acc_obj object:",
                    ptr_acc_obj,
                )
                intf = GetBestInterface(ptr_acc_obj, IAccessible)
                log.info(">>>>> get_IAccessible_from_window - intf object:", intf)
                return intf

            # Main function to get IAccessible2 from process ID
            def get_IAccessible2_from_pid(pid):
                try:
                    log.info(">>>>> get_IAccessible2_from_pid - pid:", pid)
                    log.info(">>>>> get_IAccessible2_from_pid - opening process:", pid)
                    proc = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                    log.info(
                        ">>>>> get_IAccessible2_from_pid - getting top window:", proc
                    )
                    hwnd = ctypes.windll.user32.GetTopWindow(proc)
                    log.info(">>>>> get_IAccessible2_from_pid - hwnd:", hwnd)
                    acc = get_IAccessible_from_window(hwnd)
                    log.info(">>>>> get_IAccessible2_from_pid - result acc:", acc)
                    if acc:
                        acc2 = get_IAccessible2(acc)
                        log.info(">>>>> get_IAccessible2_from_pid - result acc2:", acc)
                        return acc2
                finally:
                    log.info(">>>>> get_IAccessible2_from_pid - CloseHandle:")
                    ctypes.windll.kernel32.CloseHandle(proc)

            get_IAccessible2_from_pid(window_element.pid)

        except Exception as e:
            log.error(">>>>> !!! Exception occurred as trying to activate legacy:", e)

        log.info(">>>>> All is well!")

        # check foreground
        if foreground:
            window_element.foreground_window(move_cursor_to_center)
        if wait_time:
            time.sleep(wait_time)
        return window_element
    except ElementNotFound:
        # No matches.
        _raise_window_not_found(locator, timeout, root_element)
    raise AssertionError("Should never get here.")  # Just to satisfy typing.


def _raise_window_not_found(
    locator: Locator, timeout, root_element: Optional[_UIAutomationControlWrapper]
):
    from . import config as windows_config
    from ._match_ast import _build_locator_match

    config = windows_config()

    msg = (
        f"Could not locate window with locator: {locator!r} "
        f"(timeout: {timeout if timeout is not None else config.timeout})"
    )

    locator_match = _build_locator_match(locator)
    msg += f"\nLocator internal representation: {locator_match}"
    for warning in locator_match.warnings:
        msg += f"\nLocator warning: {warning}"

    if config.verbose_errors:
        windows_msg = ["\nFound Windows:"]
        for w in find_windows(root_element, locator="regex:.*"):
            windows_msg.append(str(w))

        msg += "\n".join(windows_msg)
    raise ElementNotFound(msg)


def find_windows(
    root_element: Optional[_UIAutomationControlWrapper],
    locator: Locator,
    search_depth: int = 1,
    timeout: Optional[float] = None,
    wait_for_window: bool = False,
    search_strategy: Literal["siblings", "all"] = "all",
) -> List[WindowElement]:
    from . import config as windows_config
    from ._find_ui_automation import (
        LocatorStrAndOrSearchParams,
        TimeoutMonitor,
        find_ui_automation_wrappers,
    )
    from ._match_ast import collect_search_params

    config = windows_config()
    window_element: WindowElement

    if timeout is None:
        timeout = config.timeout

    timeout_monitor = TimeoutMonitor(time.time() + timeout)

    ret: List[WindowElement] = []

    or_search_params = collect_search_params(locator)
    restrict_to_window_locators(or_search_params)

    locator_and_or_search_params = LocatorStrAndOrSearchParams(
        locator, or_search_params
    )

    # Use no timeout here (just a single search).
    for element in find_ui_automation_wrappers(
        locator_and_or_search_params,
        search_depth,
        root_element=root_element,
        timeout=0,
        search_strategy=search_strategy,
        wait_for_element=False,
    ):
        window_element = WindowElement(element)
        ret.append(window_element)

    while wait_for_window and not ret and not timeout_monitor.timed_out():
        # We have to keep on searching until the timeout is reached.
        # Note that we don't wait for an element (so, we should not wait
        # inside that function) but we still pass the timeout_monitor so that
        # it may return early if the timeout was reached.
        time.sleep(1 / 15.0)
        for element in find_ui_automation_wrappers(
            locator_and_or_search_params,
            search_depth,
            root_element=root_element,
            search_strategy=search_strategy,
            wait_for_element=False,
            timeout_monitor=timeout_monitor,
        ):
            window_element = WindowElement(element)
            ret.append(window_element)

    if wait_for_window and not ret:
        # No matches.
        _raise_window_not_found(locator, timeout, root_element)

    return ret
