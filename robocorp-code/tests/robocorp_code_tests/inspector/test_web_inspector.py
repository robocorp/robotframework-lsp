import pytest


@pytest.fixture
def web_inspector(datadir):
    from robocorp_ls_core import uris

    from robocorp_code.inspector.web import WEB_RECORDING_GUIDE_PATH, WEB_RESOURCES_DIR
    from robocorp_code.inspector.web._web_inspector import WebInspector

    web_inspector = WebInspector()

    assert WEB_RESOURCES_DIR.exists()
    assert WEB_RECORDING_GUIDE_PATH.exists()

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)
    assert not web_inspector.is_picker_injected()
    web_inspector.inject_picker()
    assert web_inspector.is_picker_injected()
    yield web_inspector


def test_web_inspector(web_inspector, data_regression, datadir):
    import threading

    from robocorp_ls_core import uris

    data_regression.check(locators_for(web_inspector, "#div1"), basename="div1")

    data_regression.check(locators_for(web_inspector, "#alink"), basename="alink")

    data_regression.check(locators_for(web_inspector, "#withName"), basename="withName")

    data_regression.check(locators_for(web_inspector, "#withImg"), basename="withImg")

    # Check that after a pick it's ok to close and then do a new pick.
    web_inspector.page().close()

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)
    data_regression.check(locators_for(web_inspector, "#withImg"), basename="withImg")

    # ===========================================================================
    # Check what happens if the url is changed during the (async) pick.
    # -> Changing url makes it pick 'None'
    # ===========================================================================
    event = threading.Event()
    found = []

    def on_picked(locators):
        found.append(locators)
        event.set()

    web_inspector.pick_async(on_picked)

    url = uris.from_fs_path(str(datadir / "page_to_test2.html"))
    web_inspector.open(url)

    assert event.wait(10)
    assert found == [None]

    # ===========================================================================
    # Check what happens if the browser is closed during the (async) pick.
    # -> Closing makes it pick 'None'
    # ===========================================================================
    event = threading.Event()
    found = []

    web_inspector.pick_async(on_picked)

    url = uris.from_fs_path(str(datadir / "page_to_test2.html"))
    web_inspector.open(url)

    assert event.wait(10)
    assert found == [None]

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)

    # Note: `web_inspector.pick()` not tested because it's synchronous and
    # playwright is not multi-threaded (we could in theory do a javascript
    # timer to do a click from the browser, but seems to be more work than
    # is worth).
    #
    # Uncomment for manual test:
    # web_inspector.pick()


def locators_for(web_inspector, html_id):
    import threading

    event = threading.Event()

    found = []

    def on_picked(locators):
        found.append(locators)
        event.set()

    web_inspector.pick_async(on_picked)
    web_inspector.page().click(html_id)
    assert event.wait(2), "Pick did not happen in the expected timeout."
    assert found
    locators = found[0]
    assert locators
    return web_inspector.make_full_locators(locators)
