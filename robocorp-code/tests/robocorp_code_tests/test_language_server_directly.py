import pytest
from robocorp_code_tests.fixtures import RccPatch


def test_cloud_list_workspaces_cache_invalidate(
    rcc_patch: RccPatch,
    ws_root_path: str,
    rcc_location: str,
    ci_endpoint: str,
    rcc_config_location: str,
):
    from robocorp_ls_core.constants import NULL

    from robocorp_code.rcc import AccountInfo
    from robocorp_code.robocorp_language_server import RobocorpLanguageServer

    rcc_patch.apply()

    read_stream = NULL
    write_stream = NULL
    language_server = RobocorpLanguageServer(read_stream, write_stream)
    initialization_options = {"do-not-track": True}

    language_server.m_initialize(
        rootPath=ws_root_path, initialization_options=initialization_options
    )
    language_server.m_workspace__did_change_configuration(
        {
            "robocorp": {
                "rcc": {
                    "location": rcc_location,
                    "endpoint": ci_endpoint,
                    "config_location": rcc_config_location,
                }
            }
        }
    )

    rcc = language_server._rcc
    rcc._last_verified_account_info = AccountInfo("default account", "123", "", "")

    assert language_server._cloud_list_workspaces({"refresh": False})["success"]
    rcc_patch.disallow_calls()
    assert language_server._cloud_list_workspaces({"refresh": False})["success"]

    rcc._last_verified_account_info = AccountInfo("another account", "123", "", "")

    # As account changed, the data should be fetched (as we can't due to the patching
    # the error is expected).
    with pytest.raises(AssertionError) as e:
        assert not language_server._cloud_list_workspaces({"refresh": False})["success"]

    assert "This should not be called at this time (data should be cached)." in str(e)
