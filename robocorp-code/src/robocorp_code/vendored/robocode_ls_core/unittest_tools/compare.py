"""
Helpers for doing comparissons.
"""


def compare_lines(lines_obtained, lines_expected):
    """
    :param list(str) lines_obtained:
    :param list(str) lines_expected:
    """
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
