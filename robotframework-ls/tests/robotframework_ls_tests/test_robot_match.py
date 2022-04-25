def test_robot_match():
    from robotframework_ls.impl.variable_resolve import robot_search_variable
    from robotframework_ls.impl.ast_utils import iter_robot_match_as_tokens

    robot_match = robot_search_variable("${vv}[aaa]")
    assert robot_match and robot_match.base
    found = []
    for t in iter_robot_match_as_tokens(robot_match):
        found.append((t.value, t.type))
        assert robot_match.string[t.col_offset : t.col_offset + len(t.value)] == t.value

    assert found == [
        ("vv", "base"),
        ("[", "["),
        ("aaa", "item"),
        ("]", "]"),
    ]


def test_robot_match_2():
    from robotframework_ls.impl.variable_resolve import robot_search_variable
    from robotframework_ls.impl.ast_utils import iter_robot_match_as_tokens

    robot_match = robot_search_variable("${vv}[aaa][][b]")
    assert robot_match and robot_match.base
    found = []
    for t in iter_robot_match_as_tokens(robot_match):
        found.append((t.value, t.type, t.col_offset))
        assert robot_match.string[t.col_offset : t.col_offset + len(t.value)] == t.value

    assert found == [
        ("vv", "base", 2),
        ("[", "[", 5),
        ("aaa", "item", 6),
        ("]", "]", 9),
        ("[", "[", 10),
        ("", "item", 11),
        ("]", "]", 11),
        ("[", "[", 12),
        ("b", "item", 13),
        ("]", "]", 14),
    ]


def test_find_split_index():
    from robotframework_ls.impl.variable_resolve import find_split_index

    assert find_split_index(r"a") == -1
    assert find_split_index(r"a\=0") == -1
    assert find_split_index(r"${=a}\=0") == -1
    assert find_split_index(r"b\=${b}\=${a}\=0") == -1
    assert find_split_index(r"b\=${a}\=0") == -1
    assert find_split_index(r"a\=0") == -1
    assert find_split_index(r"${a}\=0") == -1
    assert find_split_index(r"${=a}\=0") == -1
    assert find_split_index(r"a\=0\=2") == -1

    assert find_split_index(r"b\=${b}\=${a}=0") == 13
    assert find_split_index(r"b\=${a}=0") == 7
    assert find_split_index(r"b=${a}=0") == 1
    assert find_split_index(r"a=0") == 1
    assert find_split_index(r"${a}=0") == 4
    assert find_split_index(r"${=a}=0") == 5
    assert find_split_index(r"a=0\=2") == 1
