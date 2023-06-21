from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
import os
from robocorp_ls_core import uris


def test_tasks_code_lenses(
    language_server_initialized: IRobocorpLanguageServerClient,
    ws_root_path,
    initialization_options,
    data_regression,
):
    language_server = language_server_initialized
    path = os.path.join(ws_root_path, "my.py")
    uri = uris.from_fs_path(path)

    txt = """
from robocorp.tasks import task

@task
def my_entry_point():
    pass

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_code_lens(uri)
    result = ret["result"]
    assert len(result) == 2
    for r in result:
        assert r["command"]["arguments"][0].lower() == path.lower()
        r["command"]["arguments"][0] = "filepath.py"
    data_regression.check(result)
