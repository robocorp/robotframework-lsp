from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from pathlib import Path


def test_list_work_items(
    language_server_initialized: IRobocorpLanguageServerClient,
    cases: CasesFixture,
    data_regression,
):
    from robocorp_code.commands import ROBOCORP_LIST_WORK_ITEMS_INTERNAL
    from robocorp_code.protocols import ActionResultDictWorkItems

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

    def run_and_check(basename):
        ret = client.execute_command(
            ROBOCORP_LIST_WORK_ITEMS_INTERNAL, [{"robot": robot}]
        )
        action_result = ret["result"]
        assert action_result["success"]

        robot_parent = Path(robot).parent
        work_items_info = action_result["result"]
        assert work_items_info
        data_regression.check(
            make_info_relative(work_items_info, robot_parent), basename=basename
        )

    run_and_check("test_list_work_items")
    # Should have a different "new_output_workitem_path" output (even if we didn't explicitly write to the
    # previous one).
    run_and_check("test_list_work_items-2")


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
