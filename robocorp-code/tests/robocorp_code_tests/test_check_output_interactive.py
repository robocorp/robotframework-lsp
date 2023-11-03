import subprocess
import sys

import pytest


@pytest.mark.parametrize("check_timeout", [True, False])
def test_check_output_interactive(check_timeout):
    from robocorp_code.subprocess_check_output_interactive import (
        check_output_interactive,
    )

    timeout_in_seconds = 10000 if check_timeout else 1
    code = f"""import time
import sys
t = time.time()
timeout_at = t + {timeout_in_seconds}
while time.time() < timeout_at:
    sys.stdout.write('out\\n')
    sys.stderr.write('err\\n')
    time.sleep(.1)
print('the end')
"""

    stdout = []

    def on_stdout(content):
        assert content.endswith((b"\n", b"\r"))
        stdout.append(content.strip())

    stderr = []

    def on_stderr(content):
        assert content.endswith((b"\n", b"\r"))
        stderr.append(content.strip())

    def check():
        boutput = check_output_interactive(
            [sys.executable, "-c", code],
            timeout=None if (not check_timeout) else 1,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
        )
        boutput = boutput.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

        assert boutput[:8] == b"out\nout\n"
        boutput.endswith(b"the end\n")

        assert len(stdout) > 2
        assert len(stderr) > 2
        assert stdout[:2] == [b"out", b"out"]
        assert stderr[:2] == [b"err", b"err"]

        assert stdout[-1] == b"the end"

    if check_timeout:
        with pytest.raises(subprocess.TimeoutExpired):
            check()
    else:
        check()
