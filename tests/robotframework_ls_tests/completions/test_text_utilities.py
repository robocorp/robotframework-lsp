import pytest


def test_strip_leading_chars():
    from robotframework_ls.completions.text_utilities import TextUtilities

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
