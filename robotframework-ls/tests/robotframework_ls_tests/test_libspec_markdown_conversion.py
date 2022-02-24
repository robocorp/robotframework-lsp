import os


def test_libspec_markdown_conversion(cases, libspec_manager):
    from robotframework_ls.impl import libspec_markdown_conversion
    from robocorp_ls_core.basic import wait_for_non_error_condition
    from robotframework_ls.impl.libspec_markdown_conversion import (
        load_markdown_json_version,
    )

    spec_filename = cases.get_path("builtin_libs/BuiltIn.libspec")
    assert os.path.exists(spec_filename)

    conversion = libspec_markdown_conversion.LibspecMarkdownConversion(libspec_manager)
    target_json = conversion.get_markdown_json_version_filename(spec_filename)
    assert not os.path.exists(target_json)

    loaded = load_markdown_json_version(
        libspec_manager, spec_filename, os.path.getmtime(spec_filename)
    )
    assert loaded is None

    conversion.schedule_conversion_to_markdown(spec_filename)

    def generate_error_or_none():
        if not os.path.exists(target_json):
            return f"{target_json} still not created."

    wait_for_non_error_condition(generate_error_or_none)

    loaded = load_markdown_json_version(
        libspec_manager, spec_filename, os.path.getmtime(spec_filename)
    )
    assert loaded is not None
