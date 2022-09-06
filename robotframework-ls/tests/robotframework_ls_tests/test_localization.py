import pytest


def test_rf_localization_api_robot_document():
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    if not robot_version_supports_language():
        raise pytest.skip("Test requires language support.")

    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    uri = "unnamed~1"
    source = """language: pt-br
*** Casos de teste ***
My Test2
    Quando No Operation
"""
    doc = RobotDocument(uri, source, version=1, generate_ast=True)
    ast = doc.get_ast()
    locinfo = ast_utils.get_localization_info_from_model(ast)

    # i.e.: english is there by default...
    bdd_prefixes = set(locinfo.iter_bdd_prefixes_on_read())
    assert "quando" in bdd_prefixes
    assert "given" in bdd_prefixes


def test_get_lang_from_source():
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    if not robot_version_supports_language():
        raise pytest.skip("Test requires language support.")

    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    source = """language: foo"""
    doc = RobotDocument("uri", source)
    ast = doc.get_ast()
    locinfo = ast_utils.get_localization_info_from_model(ast)
    assert not locinfo.language_codes

    source = """language: pt-br"""
    doc = RobotDocument("uri", source)
    ast = doc.get_ast()
    locinfo = ast_utils.get_localization_info_from_model(ast)
    assert locinfo.language_codes == ("pt-BR",)


def test_rf_localization_api():
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    if not robot_version_supports_language():
        raise pytest.skip("Test requires language support.")

    from robot.api import get_model, Language
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import iter_keyword_usage_tokens
    from robotframework_ls.impl.ast_utils import LocalizationInfo

    model = get_model(
        """
*** Test Cases ***
My Test
    Given No Operation
    """
    )
    assert not ast_utils.collect_errors(model)

    for lang_class in Language.__subclasses__():
        lang = lang_class()
        try:
            assert lang.name
        except:
            # See: https://github.com/robotframework/robotframework/issues/4436
            assert lang.code == "en"
        assert lang.code

    lang = Language.from_name("Brazilian Portuguese")
    assert lang.name == "Brazilian Portuguese"

    lang = Language.from_name("pt-BR")
    assert lang.name == "Brazilian Portuguese"
    assert lang.code == "pt-BR"
    assert "Casos de Teste" == lang.test_cases_header
    assert "Quando" in lang.bdd_prefixes

    model = get_model(
        """
*** Casos de Teste ***
My Test
    Quando No Operation
    """,
        lang="pt-BR",
    )
    assert not ast_utils.collect_errors(model)

    lang = Language.from_name("es")
    assert lang.name == "Spanish"
    assert lang.code == "es"
    assert "Casos de prueba" == lang.test_cases_header
    assert "Entonces" in lang.bdd_prefixes

    model = get_model(
        """
*** Casos de prueba ***
My Test1
    Given No Operation
    
*** Casos de teste ***
My Test2
    Entonces No Operation
    
*** Test Cases ***
My Test3
    Quando No Operation
    """,
        # Note1: An array is supported.
        # Note2: English is always there.
        lang=["pt-BR", "es"],
    )
    ast_utils.set_localization_info_in_model(
        model,
        LocalizationInfo(("pt-BR", "es", "en")),
    )
    assert not ast_utils.collect_errors(model)
    for node_info in ast_utils.iter_indexed(model, "KeywordCall"):
        assert node_info.node.keyword in (
            "Quando No Operation",
            "Entonces No Operation",
            "Given No Operation",
        )

    for kw_usage in iter_keyword_usage_tokens(model, collect_args_as_keywords=False):
        assert kw_usage.name == "No Operation"
        assert kw_usage.prefix in ("quando", "entonces", "given")
