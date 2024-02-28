import sys
import weakref

import pytest
from robocorp_ls_core.callbacks import Callback


class _DummyLanguageServer:
    def __init__(self):
        self.on_forwarded_message = Callback()
        self.forwarded_messages = []

    def dispose(self):
        pass

    def forward_msg(self, msg):
        self.on_forwarded_message(msg)
        self.forwarded_messages.append(msg)


@pytest.fixture
def dummy_language_server():
    ret = _DummyLanguageServer()
    yield ret
    ret.dispose()


@pytest.fixture
def inspector_server_manager(dummy_language_server, log_file):
    from robocorp_code.inspector.inspector_server_manager import InspectorServerManager
    from robocorp_code.options import Setup

    Setup.options.verbose = 3
    Setup.options.log_file = log_file
    manager = InspectorServerManager(weakref.ref(dummy_language_server))
    yield manager
    try:
        manager.shutdown()
    finally:
        manager.exit()


def test_inspector_api_integrated(
    inspector_server_manager, datadir, browser_preinstalled
):
    """
    This test actually creates a server manager which will launch the inspector
    API in a different process and interact with it as needed.
    """
    inspector_api_client = inspector_server_manager.get_inspector_api_client()
    from robocorp_ls_core import uris

    assert inspector_api_client is not None
    assert inspector_api_client.send_sync_message("echo", {"arg": 1})["result"] == [
        "echo",
        1,
    ]
    assert inspector_api_client.send_sync_message("not_there", {})["error"][
        "message"
    ].startswith("Method Not Found")

    message_matcher = inspector_api_client.send_async_message("echo", {"arg": 1})
    assert message_matcher.event.wait(10)
    assert message_matcher.msg["result"] == [
        "echo",
        1,
    ]

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))

    inspector_api_client.send_sync_message("openBrowser", {"url": url})


def test_inspector_api_raw(datadir, browser_preinstalled):
    """
    This test uses the inspector API directly in the current process.
    """
    from io import BytesIO

    from robocorp_ls_core import uris

    from robocorp_code.inspector.inspector_api import InspectorApi

    read_from = BytesIO()
    write_to = BytesIO()
    inspector_api = InspectorApi(read_from, write_to)
    assert inspector_api.m_echo(1) == ("echo", 1)

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    inspector_api.m_open_browser(url)
    inspector_api.m_start_pick()

    inspector_api.m_close_browser()


def test_inspector_api_echo(inspector_server_manager):
    """
    Basic test just to see whether sending messages work.
    """
    inspector_api_client = inspector_server_manager.get_inspector_api_client()
    assert inspector_api_client is not None
    assert inspector_api_client.send_sync_message("echo", {"arg": 1})["result"] == [
        "echo",
        1,
    ]
    assert inspector_api_client.send_sync_message("not_there", {})["error"][
        "message"
    ].startswith("Method Not Found")

    message_matcher = inspector_api_client.send_async_message("echo", {"arg": 1})
    assert message_matcher.event.wait(10)
    assert message_matcher.msg["result"] == [
        "echo",
        1,
    ]


def test_inspector_url_changing(
    inspector_server_manager,
    datadir,
    data_regression,
    dummy_language_server,
    browser_preinstalled,
):
    """
    When entering pick mode, it should keep on the same mode even if the url
    changes.
    """
    from robocorp_ls_core import uris

    inspector_api_client = inspector_server_manager.get_inspector_api_client()
    assert inspector_api_client

    url = uris.from_fs_path(str(datadir / "page_to_test.html"))
    inspector_api_client.send_sync_message("openBrowser", dict(url=url, wait=True))
    inspector_api_client.send_sync_message("startPick", dict(wait=True))

    pick_message_matcher = inspector_api_client.obtain_pattern_message_matcher(
        {"method": "$/webPick"}
    )
    inspector_api_client.send_sync_message("click", {"locator": "#div1", "wait": True})
    assert pick_message_matcher.event.wait(10)

    # After the pick it shouldn't stop picking and should receive new picks.
    pick_message_matcher = inspector_api_client.obtain_pattern_message_matcher(
        {"method": "$/webPick"}
    )
    inspector_api_client.send_sync_message("click", {"locator": "#div1", "wait": True})
    assert pick_message_matcher.event.wait(10)


def test_inspector_api_usage(
    inspector_server_manager,
    datadir,
    data_regression,
    dummy_language_server,
    browser_preinstalled,
):
    """
    This simulates the API to be used to pick an element.
    """
    from robocorp_code_tests.fixtures import fix_locator
    from robocorp_ls_core import uris
    from robocorp_ls_core.basic import wait_for_condition

    inspector_api_client = inspector_server_manager.get_inspector_api_client()

    message_matcher = inspector_api_client.send_async_message(
        "browser_configure", {"wait": True}
    )
    assert message_matcher.event.wait(10)
    assert message_matcher.msg["result"] is None

    for i in range(2):  # Do 2 runs to check that we can reopen the browser.
        url = uris.from_fs_path(str(datadir / "page_to_test.html"))
        inspector_api_client.send_sync_message("openBrowser", dict(url=url, wait=True))
        inspector_api_client.send_sync_message("startPick", dict(wait=True))

        pick_message_matcher = inspector_api_client.obtain_pattern_message_matcher(
            {"method": "$/webPick"}
        )

        message_matcher = inspector_api_client.send_async_message(
            "click", {"locator": "#div1", "wait": True}
        )
        assert message_matcher.event.wait(10)
        assert message_matcher.msg["result"] is None

        assert pick_message_matcher.event.wait(10), f"No pick received (loop: {i})"
        wait_for_condition(lambda: len(dummy_language_server.forwarded_messages) >= 3)
        del dummy_language_server.forwarded_messages[:]
        msg = pick_message_matcher.msg
        locator = msg["params"]
        data_regression.check(fix_locator(locator), basename="div1Pick")

        inspector_api_client.send_sync_message("closeBrowser", dict(wait=True))


def _manual_test_inspector_repl(
    inspector_server_manager, datadir, dummy_language_server
):
    from robocorp_ls_core import uris

    inspector_api_client = inspector_server_manager.get_inspector_api_client()

    def send_msg(msg, **kwargs):
        inspector_api_client.send_sync_message(msg, kwargs)

    def _command_open():
        "Opens Browser"
        url = uris.from_fs_path(str(datadir / "page_to_test.html"))
        inspector_api_client.send_sync_message("openBrowser", dict(url=url, wait=True))

    def _command_pick():
        "Starts Picking"
        inspector_api_client.send_sync_message("startPick", dict(wait=True))

    def _command_close():
        "Closes Browser"
        inspector_api_client.send_sync_message("closeBrowser", dict(wait=True))

    commands = []
    for i, (name, val) in enumerate(sorted(sys._getframe().f_locals.items())):
        if name.startswith("_command"):
            commands.append((i, name[9:], val))

    opt_to_cmd = {}

    msg = [""]
    for i, name, cmd in commands:
        opt_to_cmd[str(i)] = cmd
        opt_to_cmd[name] = cmd

        msg.append(f"{i}. {name} ({cmd.__doc__.strip()})\n")
    msg.append("Choose option: ")

    while True:
        read = input("".join(msg))

        cmd = opt_to_cmd.get(read.strip())
        if cmd:
            cmd()
        else:
            print(f"Unrecognized input: {read}", file=sys.stderr)
