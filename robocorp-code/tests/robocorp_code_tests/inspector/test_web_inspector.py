from typing import List

import pytest
from robocorp_code_tests.fixtures import fix_locator

from robocorp_code.inspector.web._web_inspector import (
    PickedLocatorTypedDict,
    WebInspector,
)


@pytest.fixture
def web_inspector(datadir):
    from robocorp_ls_core import uris

    from robocorp_code.inspector.web import WEB_RECORDING_GUIDE_PATH, WEB_RESOURCES_DIR

    web_inspector = WebInspector()

    assert WEB_RESOURCES_DIR.exists()
    assert WEB_RECORDING_GUIDE_PATH.exists()

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)
    assert not web_inspector.is_picker_injected()
    web_inspector.inject_picker("test")
    assert web_inspector.is_picker_injected()
    yield web_inspector
    web_inspector.close_browser()


@pytest.mark.parametrize("element_id", ["div1", "alink", "withName", "withImg"])
def test_web_inspector(
    web_inspector: WebInspector, data_regression, datadir, element_id
):
    from robocorp_ls_core import uris

    data_regression.check(
        locators_for(web_inspector, f"#{element_id}"), basename=element_id
    )

    # Check that after a pick it's ok to close and then do a new pick.
    page = web_inspector.page(False)
    assert page
    page.close()

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)
    data_regression.check(locators_for(web_inspector, "#withImg"), basename="withImg")


def test_web_inspector_change_urls(
    web_inspector: WebInspector, data_regression, datadir
) -> None:
    import threading

    from robocorp_ls_core import uris
    from robocorp_ls_core.basic import wait_for_condition

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)

    # ===========================================================================
    # Check what happens if the url is changed during the (async) pick.
    # -> The picker should be reinjected
    # ===========================================================================
    event = threading.Event()
    found: List[PickedLocatorTypedDict] = []

    def on_picked(locator: PickedLocatorTypedDict):
        found.append(locator)
        event.set()

    assert web_inspector.pick_async(on_picked)

    url = uris.from_fs_path(str(datadir / "page_to_test2.html"))
    web_inspector.open(url)

    assert web_inspector.picking

    assert not event.wait(1)
    assert found == []

    # Actually do one pick which should work (even after changing the url).
    page = web_inspector.page(False)
    assert page is not None
    page.click("#withImg")

    def check_clicked():
        web_inspector.loop()
        return event.is_set()

    wait_for_condition(
        check_clicked, msg="Pick did not happen in the expected timeout."
    )

    assert found
    locator: PickedLocatorTypedDict = fix_locator(found[0])
    data_regression.check(locator, basename="withImg")
    del found[:]

    # ===========================================================================
    # Check what happens if the browser is closed during the (async) pick.
    # -> Closing makes it pick 'None'
    # ===========================================================================
    web_inspector.close_browser()

    assert found == []

    # Note: `web_inspector.pick()` not tested because it's synchronous and
    # playwright is not multi-threaded (we could in theory do a javascript
    # timer to do a click from the browser, but seems to be more work than
    # is worth).
    #
    # Uncomment for manual test:
    # web_inspector.pick()


def locators_for(web_inspector: WebInspector, html_id) -> PickedLocatorTypedDict:
    import threading

    from robocorp_ls_core.basic import wait_for_condition

    event = threading.Event()

    found = []

    def on_picked(locator: PickedLocatorTypedDict):
        found.append(locator)
        event.set()

    assert web_inspector.pick_async(on_picked)
    try:
        page = web_inspector.page(False)
        assert page
        page.click(html_id)

        def check_clicked():
            web_inspector.loop()
            return event.is_set()

        wait_for_condition(
            check_clicked, msg="Pick did not happen in the expected timeout."
        )
        assert found
        locator = found[0]
        assert locator
        return fix_locator(locator)
    finally:
        web_inspector.stop_pick_async()
