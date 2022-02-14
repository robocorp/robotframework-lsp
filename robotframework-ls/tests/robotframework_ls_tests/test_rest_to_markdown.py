def test_rest_to_markdown():
    from robotframework_ls.impl.robot_specbuilder import _rest_to_markdown

    initial = """******************************
This is example of rst on GFG
******************************

*GeeksforGeeks in italic*

**GeeksforGeeks in bold**

`Gfg website<www.geeksforgeeks.org>`

``GeeksforGeeks in vebatim``
"""
    assert (
        _rest_to_markdown(initial)
        == """# This is example of rst on GFG

*GeeksforGeeks in italic*

**GeeksforGeeks in bold**

Gfg website<www.geeksforgeeks.org>

`GeeksforGeeks in vebatim`
"""
    )
