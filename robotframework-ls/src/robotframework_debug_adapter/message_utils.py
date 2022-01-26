from typing import Optional, Tuple


def extract_source_and_line_from_message(msg) -> Optional[Tuple[str, int]]:
    """
    :param msg:
        Something as:
        Error in file 'C:/Users/.../case_import_failure.robot' on line 2
    """
    if msg:
        first_line = msg.split("\n")[0]
        import re

        m = re.search(r"file\s'(.*)'\son\sline\s(\d+)", first_line)
        if m:
            return m.group(1), int(m.group(2))
    return None
