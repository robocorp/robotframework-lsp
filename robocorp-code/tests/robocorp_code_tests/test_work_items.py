import time
from pathlib import Path

from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture


def test_list_work_items(
    language_server_initialized: IRobocorpLanguageServerClient,
    cases: CasesFixture,
    data_regression,
):
    from robocorp_code.commands import ROBOCORP_LIST_WORK_ITEMS_INTERNAL
    from robocorp_code.protocols import ActionResultDictWorkItems, WorkItemsInfo
    from robocorp_code.robocorp_language_server import RobocorpLanguageServer

    client = language_server_initialized

    robot = cases.get_path("custom_envs/work_items/robot.yaml")

    # Fail: robot required
    ret = client.execute_command(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, [])
    action_result: ActionResultDictWorkItems = ret["result"]
    assert not action_result["success"]

    # Fail: robot does not exist
    ret = client.execute_command(
        ROBOCORP_LIST_WORK_ITEMS_INTERNAL,
        [{"robot": "does not exist", "increment_output": True}],
    )
    action_result = ret["result"]
    assert not action_result["success"]

    def run_and_check(
        basename, output_prefix=None, increment_output: bool = True
    ) -> WorkItemsInfo:
        dct: dict = {"robot": robot}
        if output_prefix:
            dct["output_prefix"] = output_prefix
        dct["increment_output"] = increment_output

        ret = client.execute_command(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, [dct])
        action_result = ret["result"]
        assert action_result["success"]

        robot_parent = Path(robot).parent
        work_items_info = action_result["result"]
        assert work_items_info
        data_regression.check(
            make_info_relative(work_items_info, robot_parent), basename=basename
        )

        return work_items_info

    run_and_check("test_list_work_items")

    # new_output_workitem_path is empty now.
    run_and_check("test_list_work_items-1-no-increment", increment_output=False)

    # Should have a different "new_output_workitem_path" output (even if we
    # didn't explicitly write to the previous one).
    run_and_check("test_list_work_items-2")

    original = RobocorpLanguageServer.TIMEOUT_TO_CONSIDER_LAST_RUN_FRESH
    try:
        RobocorpLanguageServer.TIMEOUT_TO_CONSIDER_LAST_RUN_FRESH = 0.5
        run_and_check("test_list_work_items-interactive-1", "interactive-")
        run_and_check("test_list_work_items-interactive-2", "interactive-")

        # Consider only filesystem after timeout elapses
        time.sleep(RobocorpLanguageServer.TIMEOUT_TO_CONSIDER_LAST_RUN_FRESH)
        info_1: WorkItemsInfo = run_and_check(
            "test_list_work_items-interactive-1", "interactive-"
        )
        run_and_check("test_list_work_items-interactive-2", "interactive-")

        time.sleep(RobocorpLanguageServer.TIMEOUT_TO_CONSIDER_LAST_RUN_FRESH)

        # Check that it's computed based only on what's available in the
        # filesystem now that the timeout elapsed.
        p = Path(info_1["new_output_workitem_path"])
        p.parent.mkdir(exist_ok=True)
        p.write_text("{}")

        run_and_check("test_list_work_items-interactive-3", "interactive-")
    finally:
        RobocorpLanguageServer.TIMEOUT_TO_CONSIDER_LAST_RUN_FRESH = original


def make_info_relative(work_items_info, robot_parent):
    def make_relative(val: str) -> str:
        if not val:
            return val
        return str(Path(val).relative_to(robot_parent)).replace("\\", "/")

    new = {}
    for key, val in work_items_info.items():
        if key in (
            "robot_yaml",
            "input_folder_path",
            "output_folder_path",
            "new_output_workitem_path",
        ):
            new[key] = make_relative(val)

        elif key in ("input_work_items", "output_work_items"):
            new_lst = []
            new[key] = new_lst
            for item in val:
                d = {}
                new_lst.append(d)
                for k, v in item.items():
                    if k == "json_path":
                        d[k] = make_relative(v)
                    else:
                        d[k] = v

        else:
            new[key] = val
    return new


def test_work_items_removal(
    language_server_initialized: IRobocorpLanguageServerClient, cases: CasesFixture
):
    from robocorp_ls_core.basic import wait_for_condition

    from robocorp_code.commands import ROBOCORP_LIST_WORK_ITEMS_INTERNAL

    client = language_server_initialized

    robot = cases.get_path("custom_envs/work_items/robot.yaml")

    paths = set()

    def run():
        ret = client.execute_command(
            ROBOCORP_LIST_WORK_ITEMS_INTERNAL,
            [{"robot": robot, "increment_output": True}],
        )
        action_result = ret["result"]
        assert action_result["success"]

        work_items_info = action_result["result"]
        # Check that it's computed based only on what's available in the
        # filesystem now that the timeout elapsed.
        p = Path(work_items_info["new_output_workitem_path"])
        p.parent.mkdir(exist_ok=True)
        p.write_text("{}")
        return p

    for _ in range(10):
        paths.add(run())

    assert len(paths) == 10

    def condition():
        found = set()
        for p in paths:
            if p.exists():
                found.add(p.parent.name)

        # 6 items are kept (the last 5 + latest run).
        return found == {
            "run-6",
            "run-7",
            "run-8",
            "run-9",
            "run-10",
            "run-11",
        }

    def msg():
        exists = ""
        removed = ""
        for p in paths:
            if p.exists():
                exists += f"{p}\n"
            else:
                removed += f"{p}\n"
        return f"Exists:\n{exists}\n\nRemoved:\n{removed}\n"

    wait_for_condition(condition, msg, timeout=5)


def test_verify_library_version(
    language_server_initialized: IRobocorpLanguageServerClient, tmpdir
):
    from robocorp_code.commands import ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL

    client = language_server_initialized

    ret = client.execute_command(
        ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL,
        [{"conda_prefix": str(tmpdir), "libs_and_version": [["rpaframework", "11.1"]]}],
    )
    result = ret["result"]
    assert not result["success"]
    assert "golden-ee.yaml to exist" in result["message"]

    golden_ee = tmpdir.join("golden-ee.yaml")
    golden_ee.write(
        """
- name: rpaframework
  version: 11.1.2
  origin: pypi
- name: rpaframework-core
  version: 6.4.0
  origin: pypi
- name: rpaframework-dialogs
  version: 0.3.2
  origin: pypi
"""
    )

    for v in ("10", "11", "11.1", "11.1.1", "11.1.2"):
        ret = client.execute_command(
            ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL,
            [{"conda_prefix": str(tmpdir), "libs_and_version": [["rpaframework", v]]}],
        )
        result = ret["result"]
        assert result["success"]
        assert result["result"] == {"library": "rpaframework", "version": "11.1.2"}

    for v in ("12", "11.2", "11.1.3"):
        ret = client.execute_command(
            ROBOCORP_VERIFY_LIBRARY_VERSION_INTERNAL,
            [{"conda_prefix": str(tmpdir), "libs_and_version": [["rpaframework", v]]}],
        )
        result = ret["result"]
        assert not result["success"]
        assert result["result"] == None
