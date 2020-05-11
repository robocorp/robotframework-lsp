import re


def compare_lines(lines_obtained, lines_expected):
    import textwrap

    if lines_obtained == lines_expected:
        return

    msg = "Lines differ.\n"
    diff_lines = []
    lines_obtained.insert(0, "=== Obtained ===")
    lines_expected.insert(0, "=== Expected ===")
    for i in range(max(len(lines_obtained), len(lines_expected))):
        try:
            l1 = textwrap.wrap(lines_obtained[i])
        except IndexError:
            l1 = []
        try:
            l2 = textwrap.wrap(lines_expected[i])
        except IndexError:
            l2 = []

        for j in range(max(len(l1), len(l2))):
            try:
                line1 = l1[j]
            except:
                line1 = ""
            try:
                line2 = l2[j]
            except:
                line2 = ""

            if i == 0:
                sep = "    "
            else:
                sep = " == " if line1 == line2 else " != "

            # Add the line and the contents of each side.
            diff_lines.append(
                str(i) + ". " + line1 + (" " * (81 - len(line1))) + sep + line2
            )

    msg += "\n".join(diff_lines)
    raise AssertionError(msg)


def update_version(version, filepath):
    with open(filepath, "r") as stream:
        contents = stream.read()

    new_contents = fix_contents_version(contents, version)
    if contents != new_contents:
        with open(filepath, "w") as stream:
            stream.write(new_contents)


def fix_contents_version(contents, version):
    contents = re.sub(
        r"(version\s*=\s*)\"\d+\.\d+\.\d+", r'\1"%s' % (version,), contents
    )
    contents = re.sub(
        r"(__version__\s*=\s*)\"\d+\.\d+\.\d+", r'\1"%s' % (version,), contents
    )
    contents = re.sub(
        r"(\"version\"\s*:\s*)\"\d+\.\d+\.\d+", r'\1"%s' % (version,), contents
    )

    return contents


def test_lines():
    """
    Things we must match:

        version="0.0.1"
        "version": "0.0.1",
        __version__ = "0.0.1"
    """

    contents = fix_contents_version(
        """
        version="0.0.1"
        version = "0.0.1"
        "version": "0.0.1",
        "version":"0.0.1",
        "version" :"0.0.1",
        __version__ = "0.0.1"
        """,
        "3.7.1",
    )

    expected = """
        version="3.7.1"
        version = "3.7.1"
        "version": "3.7.1",
        "version":"3.7.1",
        "version" :"3.7.1",
        __version__ = "3.7.1"
        """

    compare_lines(contents.splitlines(), expected.splitlines())


if __name__ == "__main__":
    test_lines()
