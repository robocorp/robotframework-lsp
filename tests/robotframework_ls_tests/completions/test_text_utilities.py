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


def test_matches_robot_keyword():
    from robotframework_ls.impl.text_utilities import matches_robot_keyword
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    keyword_name_call_text = 'I execute "ls"'
    keyword_name = 'I execute "${cmd:[^"]+}"'
    assert matches_robot_keyword(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    keyword_name_call_text = 'I execute "ls" f'
    assert not matches_robot_keyword(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    keyword_name_call_text = 'f I execute "ls"'
    assert not matches_robot_keyword(
        normalize_robot_name(keyword_name_call_text), normalize_robot_name(keyword_name)
    )

    # Should work on the regular case too.
    assert matches_robot_keyword(
        normalize_robot_name("rar{a"), normalize_robot_name("rar{a")
    )

    assert matches_robot_keyword(
        normalize_robot_name("rara"), normalize_robot_name("rara")
    )
