import pytest


@pytest.fixture
def web_inspector(datadir):
    from robocorp_code.inspector.web import WEB_RECORDING_GUIDE_PATH, WEB_RESOURCES_DIR
    from robocorp_code.inspector.web._web_inspector import WebInspector
    from robocorp_ls_core import uris

    web_inspector = WebInspector()

    assert WEB_RESOURCES_DIR.exists()
    assert WEB_RECORDING_GUIDE_PATH.exists()

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    web_inspector.open(url)
    assert not web_inspector.is_picker_injected()
    web_inspector.inject_picker()
    assert web_inspector.is_picker_injected()
    yield web_inspector


def test_web_inspector(web_inspector, data_regression):
    data_regression.check(locators_for(web_inspector, "#div1"), basename="div1")

    data_regression.check(locators_for(web_inspector, "#alink"), basename="alink")

    data_regression.check(locators_for(web_inspector, "#withName"), basename="withName")

    data_regression.check(locators_for(web_inspector, "#withImg"), basename="withImg")


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
