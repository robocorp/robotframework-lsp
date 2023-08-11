import sys
from pathlib import Path

from robocorp_code.protocols import IRcc
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def test_prebuilt_environments(rcc: IRcc, tmpdir):
    # We download the env and check that we can create it in the ci.
    import io

    import requests
    import robocorp_code

    repo_root = Path(robocorp_code.__file__).parent.parent.parent
    assert repo_root.name == "robocorp-code"

    rcc_ts = repo_root / "vscode-client" / "src" / "rcc.ts"
    text = rcc_ts.read_text("utf-8")
    conda_yaml = repo_root / "bin" / "create_env"

    if sys.platform == "win32":
        check = "const BASENAME_PREBUILT_WIN_AMD64 = "
        conda_yaml /= "conda_vscode_windows_amd64.yml"
    elif "linux" in sys.platform:
        check = "const BASENAME_PREBUILT_LINUX_AMD64 = "
        conda_yaml /= "conda_vscode_linux_amd64.yml"
    elif sys.platform == "darwin":
        check = "const BASENAME_PREBUILT_DARWIN = "
        conda_yaml /= "conda_vscode_darwin_amd64.yml"
    else:
        raise AssertionError("Unexpected platform: {sys.platform}.")

    # The code we're searching for is something as:
    # const BASENAME_PREBUILT_WIN_AMD64 = "978947424da5b5d4_windows_amd64.zip";
    for line in text.splitlines():
        if line.startswith(check):
            break
    else:
        raise AssertionError(f"Could not find line starting with: {check}.")

    basename_url = line.split("=")[-1].strip().replace('"', "").replace(";", "")
    full_url = f"https://downloads.robocorp.com/holotree/bin/{basename_url}"
    p = Path(str(tmpdir / basename_url))

    if not p.exists():
        log.info(f"Downloading to: {p}")
        response = requests.get(full_url)
        assert response.status_code == 200
        b = io.BytesIO(response.content)
        p.write_bytes(b.read())
        log.info(f"Finished downloading to: {p}")

    assert rcc.holotree_import(p, enable_shared=True).success

    assert rcc.holotree_variables(
        conda_yaml, "test-prebuilt-environments", no_build=True
    ).success
