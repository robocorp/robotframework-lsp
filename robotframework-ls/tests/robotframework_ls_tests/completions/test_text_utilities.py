import pytest


def test_strip_leading_chars():
    from robotframework_ls.impl.text_utilities import TextUtilities

    text_utilities = TextUtilities("** f")
    assert text_utilities.strip_leading_chars("*")
    assert text_utilities.text == " f"
    assert not text_utilities.strip_leading_chars("*")
    assert not text_utilities.strip_leading_chars("f")
    assert text_utilities.strip_leading_chars(" ")
    assert text_utilities.text == "f"
    assert text_utilities.strip_leading_chars("f")
    assert text_utilities.text == ""
    assert not text_utilities.strip_leading_chars(" ")
    with pytest.raises(AssertionError):
        text_utilities.strip_leading_chars("")  # char size must be == 1


def test_matches_name_with_variables():
    from robotframework_ls.impl.text_utilities import matches_name_with_variables
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    keyword_name_call_text = 'I execute "ls"'
    keyword_name = 'I execute "${cmd:[^"]+}"'
    assert matches_name_with_variables(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    keyword_name_call_text = 'I execute "ls" f'
    assert not matches_name_with_variables(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    keyword_name_call_text = 'f I execute "ls"'
    assert not matches_name_with_variables(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    # Should work on the regular case too.
    assert matches_name_with_variables(
        normalize_robot_name("rar{a"), normalize_robot_name("rar{a")
    )

    assert matches_name_with_variables(
        normalize_robot_name("rara"), normalize_robot_name("rara")
    )


def test_matches_name_with_variables_with_custom_regexp():
    from robotframework_ls.impl.text_utilities import matches_name_with_variables
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    keyword_name_call_text = r"Today is 2022-22-22"
    keyword_name = r"Today is ${date:\d{4}-\d{2}-\d{2}}"
    assert matches_name_with_variables(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    keyword_name_call_text = r"Today is not"
    keyword_name = r"Today is ${date:\d{4}-\d{2}-\d{2}}"
    assert not matches_name_with_variables(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )


def test_iter_dotted_names():
    from robotframework_ls.impl.text_utilities import iter_dotted_names

    assert list(iter_dotted_names("")) == []
    assert list(iter_dotted_names("a")) == []
    assert list(iter_dotted_names("a.b")) == [("a", "b")]
    assert list(iter_dotted_names(".a.b.")) == [
        ("", "a.b."),
        (".a", "b."),
        (".a.b", ""),
    ]
    assert list(iter_dotted_names("a.b.")) == [("a", "b."), ("a.b", "")]
    assert list(iter_dotted_names("a.b.c")) == [("a", "b.c"), ("a.b", "c")]


def test_get_indent():
    from robotframework_ls.impl.text_utilities import TextUtilities

    assert TextUtilities("    abc").get_indent() == "    "
    assert TextUtilities("\t  abc").get_indent() == "\t  "
