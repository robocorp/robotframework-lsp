from robocorp_ls_core.protocols import ILanguageServerClient
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture


def test_customize_interpreter(
    language_server_io: ILanguageServerClient, workspace_dir: str, cases: CasesFixture
):
    from robocorp_ls_core import uris
    import os
    from pathlib import Path
    from robotframework_ls.impl.robot_workspace import RobotDocument

    language_server = language_server_io

    cases.copy_to("custom_env", workspace_dir)

    language_server.initialize(workspace_dir, process_id=os.getpid())
    case1_robot: Path = Path(workspace_dir) / "env1" / "caselib1.robot"
    assert case1_robot.exists()
    uri_case1 = uris.from_fs_path(str(case1_robot))

    doc = RobotDocument(uri_case1)
    i_line = doc.find_line_with_contents("    verify lib1")

    language_server.open_doc(uri_case1, 1)

    ret = language_server.find_definitions(uri_case1, i_line, 6)
    result = ret["result"]
    assert not result

    # Now, customize it with the plugins.
    plugins_dir = cases.get_path("custom_env/plugins")

    add_plugins_result = language_server.execute_command(
        "robot.addPluginsDir", [plugins_dir]
    )
    assert add_plugins_result["result"]

    ret = language_server.find_definitions(uri_case1, i_line, 6)
    result = ret["result"]
    assert result
    check = next(iter(result))
    assert check["uri"].endswith("lib1.py")

    # Check with another case
    case2_robot: Path = Path(workspace_dir) / "env2" / "caselib2.robot"
    assert case2_robot.exists()
    uri_case2 = uris.from_fs_path(str(case2_robot))
    doc = RobotDocument(uri_case2)
    i_line = doc.find_line_with_contents("    verify lib2")
    ret = language_server.find_definitions(uri_case2, i_line, 6)
    result = ret["result"]
    assert result
    check = next(iter(result))
    assert check["uri"].endswith("lib2.py")
