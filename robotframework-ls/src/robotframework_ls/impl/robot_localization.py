from typing import Tuple, Set, Union, Iterator, Optional, Any
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import ILocalizationInfo

log = get_logger(__name__)


def _get_lang_from_code(language_code, __code_to_language_cache={}):
    try:
        return __code_to_language_cache[language_code]
    except KeyError:
        from robot.api import Language

        try:
            __code_to_language_cache[language_code] = Language.from_name(language_code)
        except:
            log.exception(f"Unable to load language: {language_code}")
            # Cache as None
            __code_to_language_cache[language_code] = None

        return __code_to_language_cache[language_code]


class LocalizationInfo:
    def __init__(self, language_codes: Union[Tuple[str, ...], str]):
        if isinstance(language_codes, str):
            language_codes = (language_codes,)
        self._language_codes: Tuple[str, ...] = language_codes

        self._last_bdd_prefixes_cache_key: Optional[Set[str]] = None
        self._bdd_prefixes: Optional[Set[str]] = None

    def __str__(self):
        return f"LocalizationInfo({self._language_codes})"

    @property
    def language_codes(self) -> Tuple[str, ...]:
        return self._language_codes  # Note: could actually be language code or name.

    def iter_languages_on_write(
        self,
    ) -> Iterator[Any]:  # Actually Iterator[robot.api.Language]
        from robotframework_ls.impl.robot_version import robot_version_supports_language

        if robot_version_supports_language():
            languages = set()

            found = False

            if self._language_codes:
                # i.e.: prefer language specified locally.
                for lang_code in set(self._language_codes):
                    lang = _get_lang_from_code(lang_code)
                    if lang is None:
                        log.info("Could not find language: %s", lang_code)
                    else:
                        if lang not in languages:
                            languages.add(lang)
                            found = True
                            yield lang
                if found:
                    return

            # Not found locally: fall back to global.
            global_localization_info = get_global_localization_info()

            if global_localization_info.language_codes:
                for lang_code in set(global_localization_info.language_codes):
                    lang = _get_lang_from_code(lang_code)
                    if lang is None:
                        log.info(
                            "Could not find language: %s (set in global)", lang_code
                        )
                    else:
                        if lang not in languages:
                            languages.add(lang)
                            found = True
                            yield lang

                if found:
                    return

            # No language defined locally nor globally: just use english.
            lang = _get_lang_from_code("en")
            if lang is None:
                log.critical("en lang returning None (this should not be possible).")
            else:
                yield lang

    def iter_bdd_prefixes_on_read(self) -> Iterator[str]:
        """
        Note that we specify the reason for iterating because for instance, when
        writing code we could want just the completions for the specified
        language in the file and while reading (i.e.: analyzing) we'd want it
        for all languages.
        """
        from robotframework_ls.impl.robot_version import robot_version_supports_language

        global_localization_info = get_global_localization_info()
        global_language_codes = set(global_localization_info.language_codes)
        if self._last_bdd_prefixes_cache_key != global_language_codes:
            self._bdd_prefixes = None  # Clear cache

        if self._bdd_prefixes is None:
            from robotframework_ls.impl.robot_constants import BDD_PREFIXES

            bdd_prefixes: Set[str] = set()
            bdd_prefixes.update(BDD_PREFIXES)

            if robot_version_supports_language():
                use_language_codes = set(global_language_codes)
                use_language_codes.update(self._language_codes)

                for lang_code in use_language_codes:
                    if lang_code.lower() in ("en", "english"):
                        # Just for English use our constants (which are already loaded).
                        continue

                    else:
                        lang = _get_lang_from_code(lang_code)
                        if lang is not None:
                            for prefix in iter(lang.bdd_prefixes):
                                # Note: iterating over the same language multiple
                                # times would be ok here.
                                bdd_prefixes.add(prefix.lower())

            self._last_bdd_prefixes_cache_key = global_language_codes
            self._bdd_prefixes = bdd_prefixes

        yield from iter(self._bdd_prefixes)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ILocalizationInfo = check_implements(self)


class _LocalizationInfoHolder:
    localization_info = LocalizationInfo("en")  # Default is just English.


def set_global_localization_info(localization_info: LocalizationInfo):
    log.debug(
        "Setting global localization language: %s", localization_info.language_codes
    )
    _LocalizationInfoHolder.localization_info = localization_info


def get_global_localization_info() -> LocalizationInfo:
    return _LocalizationInfoHolder.localization_info


def set_global_from_config(config):
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LANGUAGE,
    )

    try:
        language_codes = config.get_setting(OPTION_ROBOT_LANGUAGE, list, [])
        if not language_codes:
            language_codes = "en"
        set_global_localization_info(LocalizationInfo(language_codes))

    except:
        log.exception(f"Error setting localization info from configuration.")
        # Fallback to English.
        set_global_localization_info(LocalizationInfo("en"))
