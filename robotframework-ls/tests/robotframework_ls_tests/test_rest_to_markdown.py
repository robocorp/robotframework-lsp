def test_rest_to_markdown_code_block():
    from robotframework_ls.impl.robot_specbuilder import _rest_to_markdown

    initial = """
Do something with rest.
        
.. code-block:: robotframework

    FOR    ${a}   IN    @{b}
        Do Something
    END
"""

    assert (
        _rest_to_markdown(initial)
        == """Do something with rest.

```robotframework
FOR    ${a}   IN    @{b}
    Do Something
END
```
"""
    )


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
