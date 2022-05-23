def main():
    from pathlib import Path
    from robot.running.runkwregister import RUN_KW_REGISTER
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    import inspect

    p = Path(__file__)
    impl_folder = p.parent.parent / "src" / "robotframework_ls" / "impl"
    assert impl_folder.exists()

    keywords_in_args = impl_folder / "keywords_in_args.py"

    # Import to force the registry.
    from robot.libraries.BuiltIn import BuiltIn

    KEYWORD_NAME_TO_KEYWORD_INDEX = {
        "run_keywords": 1,
        # These aren't in all RF versions, so, hardcode it.
        "run_keyword_if_all_critical_tests_passed": 1,
        "run_keyword_if_any_critical_tests_failed": 1,
        "for_each_input_work_item": 1,
    }
    KEYWORD_NAME_TO_CONDITION_INDEX = {
        "evaluate": 1,
        # Variables mays use the format : Set Global Variable    $var_name
        # So, we need to acknowledge that...
        "set_global_variable": 1,
        "set_local_variable": 1,
        "set_suite_variable": 1,
        "set_task_variable": 1,
        "set_test_variable": 1,
    }

    for method in dir(BuiltIn):
        if method.startswith("_"):
            continue

        m = getattr(BuiltIn, method)
        try:
            signature = inspect.signature(m)
        except:
            continue
        if "condition" in signature.parameters:
            KEYWORD_NAME_TO_CONDITION_INDEX[method] = 1
            print(method)
    print("Found", len(KEYWORD_NAME_TO_CONDITION_INDEX), "keywords with conditions\n\n")

    for libname, keyword in RUN_KW_REGISTER._libs.items():
        for keyword_name, arg_i in keyword.items():

            if keyword_name in (
                "pass_execution_if",
                "return_from_keyword_if",
                "set_variable_if",
            ):
                continue
            if arg_i > 0:
                KEYWORD_NAME_TO_KEYWORD_INDEX[keyword_name] = arg_i
                print(libname, keyword_name, arg_i)

    print(
        "Found", len(KEYWORD_NAME_TO_KEYWORD_INDEX), "keywords with keyword arguments"
    )

    dict_repr = "{\n"
    for key, val in KEYWORD_NAME_TO_KEYWORD_INDEX.items():
        if key in ("pass_execution_if", "returnfromkeywordif"):
            continue
        normalized_key = normalize_robot_name(key)
        dict_repr += f'    "{normalized_key}": {val},  # {key}\n'
    dict_repr += "}"

    dict_repr_condition = "{\n"
    for key, val in KEYWORD_NAME_TO_CONDITION_INDEX.items():
        normalized_key = normalize_robot_name(key)
        dict_repr_condition += f'    "{normalized_key}": {val},  # {key}\n'
    dict_repr_condition += "}"

    content = f"""# WARNING: auto-generated file. Do NOT edit.
# If this file needs to be edited, change `codegen_kewords_in_args.py` and rerun.
KEYWORD_NAME_TO_KEYWORD_INDEX = {dict_repr}
KEYWORD_NAME_TO_CONDITION_INDEX = {dict_repr_condition}
"""

    keywords_in_args.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
