from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from pathlib import Path
import time


def test_list_work_items(
    language_server_initialized: IRobocorpLanguageServerClient,
    cases: CasesFixture,
    data_regression,
):
    from robocorp_code.commands import ROBOCORP_LIST_WORK_ITEMS_INTERNAL
    from robocorp_code.protocols import ActionResultDictWorkItems
    from robocorp_code.robocorp_language_server import RobocorpLanguageServer
    from robocorp_code.protocols import WorkItemsInfo

    client = language_server_initialized

    robot = cases.get_path("custom_envs/work_items/robot.yaml")

    # Fail: robot required
    ret = client.execute_command(ROBOCORP_LIST_WORK_ITEMS_INTERNAL, [])
    action_result: ActionResultDictWorkItems = ret["result"]
    assert not action_result["success"]

    # Fail: robot does not exist
    ret = client.execute_command(
        ROBOCORP_LIST_WORK_ITEMS_INTERNAL, [{"robot": "does not exist"}]
    )
    action_result = ret["result"]
    assert not action_result["success"]

    def run_and_check(basename, output_prefix=None) -> WorkItemsInfo:
        dct = {"robot": robot}
        if output_prefix:
            dct["output_prefix"] = output_prefix
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
    from robocorp_code.commands import ROBOCORP_LIST_WORK_ITEMS_INTERNAL
    from robocorp_ls_core.basic import wait_for_condition

    client = language_server_initialized

    robot = cases.get_path("custom_envs/work_items/robot.yaml")

    paths = set()

    def run():
        ret = client.execute_command(
            ROBOCORP_LIST_WORK_ITEMS_INTERNAL, [{"robot": robot}]
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
        found = 0
        for p in paths:
            if p.exists():
                found += 1
        return found == 5

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
