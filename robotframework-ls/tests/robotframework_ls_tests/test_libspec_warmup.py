from robotframework_ls.impl.libspec_manager import LibspecManager
import py


def test_libspec_warmup_find_rf_libraries(
    libspec_manager: LibspecManager, tmpdir: py.path.local
):
    rpa = tmpdir.join("RPA")
    rpa.mkdir()
    browser = rpa.join("Browser")
    browser.mkdir()

    tmpdir.join("SSHLibrary.py").write_text("something", encoding="utf-8")

    libspec_warmup = libspec_manager._libspec_warmup
    assert set(
        libspec_warmup.find_rf_libraries(libspec_manager, tracked_folders=[str(tmpdir)])
    ) == {"SSHLibrary", "RPA.Browser"}
