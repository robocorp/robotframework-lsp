from robotframework_ls.impl.libspec_manager import LibspecManager
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
import pytest


def _generate_new_libspec(libspec_manager: LibspecManager, cases: CasesFixture):
    filename = cases.get_path("case_argspec/case_argspec.py")
    libspec_manager._create_libspec(filename)
    # Now, copy the spec and put it in the proper place.


@pytest.mark.parametrize("name", ["case_v2", "case_v3", "case_v4"])
def test_spec_doc_builder(
    libspec_manager: LibspecManager,
    cases: CasesFixture,
    original_datadir,
    data_regression,
    name: str,
):
    from robotframework_ls.impl.robot_specbuilder import JsonDocBuilder

    # Uncomment to generate for the current version
    # Note: must be manually copied to the proper place after the generation.
    # _generate_new_libspec(libspec_manager, cases)
    # return

    from robotframework_ls.impl.robot_specbuilder import SpecDocBuilder

    p = original_datadir / f"{name}.libspec"
    builder = SpecDocBuilder()
    library_doc = builder.build(str(p))
    assert library_doc.doc_format in ("ROBOT", "HTML")
    assert library_doc, f"Unable to generate library doc for: {p}"
    assert len(library_doc.keywords) == 7

    check: dict = {}
    for keyword in library_doc.keywords:
        args = keyword.args

        check[keyword.name] = {
            "args": [
                {
                    "name": arg.arg_name,
                    "is_keyword": arg.is_keyword_arg,
                    "is_star": arg.is_star_arg,
                    "arg_type": arg.arg_type,
                    "default_value": arg.default_value,
                    "original_arg": arg.original_arg,
                }
                for arg in args
            ]
        }

    if library_doc.data_types:
        check["data_types"] = [
            data_type.to_dictionary() for data_type in library_doc.data_types
        ]
    data_regression.check(check, basename=f"{p.name}_expected")

    assert library_doc.convert_docs_to_markdown()
    data_regression.check(
        library_doc.to_dictionary(), basename=f"{p.name}_json_expected"
    )

    import json

    s = json.dumps(library_doc.to_dictionary())
    recreated = JsonDocBuilder().build_from_dict("filename", json.loads(s))

    data_regression.check(recreated.to_dictionary(), basename=f"{p.name}_json_expected")
