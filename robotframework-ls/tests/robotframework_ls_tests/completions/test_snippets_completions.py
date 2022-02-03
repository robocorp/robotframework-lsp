def _get_version():
    from robotframework_ls.impl.robot_version import get_robot_major_version

    v = get_robot_major_version()
    if v <= 4:
        return "rf4"
    return "rf5"


def test_snippets_completions(data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import snippets_completions

    doc = RobotDocument("unused", source="""for""")
    completions = snippets_completions.complete(CompletionContext(doc))

    data_regression.check(
        completions, basename="test_snippets_completions_" + _get_version()
    )


def test_snippets_completions2(data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import snippets_completions

    doc = RobotDocument("unused", source="""FoR""")
    completions = snippets_completions.complete(CompletionContext(doc))

    data_regression.check(
        completions, basename="test_snippets_completions_" + _get_version()
    )


def test_snippets_completions3(data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import snippets_completions

    doc = RobotDocument("unused", source="""t""")
    completions = snippets_completions.complete(CompletionContext(doc))

    data_regression.check(
        completions, basename="test_snippets_completions_try_" + _get_version()
    )
