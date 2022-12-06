from typing import Optional, Set, List, Dict, Iterator, Sequence
import weakref

from robocorp_ls_core.protocols import ITestInfoFromSymbolsCacheTypedDict
from robotframework_ls.impl.protocols import (
    ILibraryDoc,
    IRobotDocument,
    ISymbolsJsonListEntry,
    ICompletionContext,
    ISymbolKeywordInfo,
)
import typing
import threading
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class BaseSymbolsCache:
    _library_info: "Optional[weakref.ReferenceType[ILibraryDoc]]"
    _doc: "Optional[weakref.ReferenceType[IRobotDocument]]"

    def __init__(
        self,
        json_list: List[ISymbolsJsonListEntry],
        library_info: Optional[ILibraryDoc],
        doc: Optional[IRobotDocument],
        keywords_used: Set[str],
        uri: Optional[str],  # Always available if generated from doc.
        test_info: Optional[List[ITestInfoFromSymbolsCacheTypedDict]],
        global_variables_defined: Optional[Set[str]] = None,
        variable_references: Optional[Set[str]] = None,
    ):
        from robocorp_ls_core.cache import LRUCache

        self._uri = uri
        if library_info is not None:
            self._library_info = weakref.ref(library_info)
        else:
            self._library_info = None

        if doc is not None:
            self._doc = weakref.ref(doc)
        else:
            self._doc = None

        self._json_list = json_list
        self._keywords_used = keywords_used
        self._check_name_with_vars_cache_usage: LRUCache[str, bool] = LRUCache()
        self._check_name_with_vars_cache_usage_lock = threading.Lock()

        if global_variables_defined is None:
            global_variables_defined = set()
        self._global_variables_defined: Set[str] = global_variables_defined

        if variable_references is None:
            variable_references = set()
        self._variable_references: Set[str] = variable_references

        self._test_info = test_info

    def get_test_info(self) -> Optional[List[ITestInfoFromSymbolsCacheTypedDict]]:
        return self._test_info

    def get_uri(self) -> Optional[str]:
        return self._uri

    def has_keyword_usage(self, normalized_keyword_name: str) -> bool:
        ret = normalized_keyword_name in self._keywords_used
        if ret or "{" not in normalized_keyword_name:
            return ret

        with self._check_name_with_vars_cache_usage_lock:
            # The LRU is not thread safe, so, we need a lock (not ideal though as
            # it's slow)... using lru_cache would be thread safe, but we don't want to put
            # 'self' in it (so, we'd need some tricks to use it).
            # For now just use a lock for simplicity.
            found_in_cache = self._check_name_with_vars_cache_usage.get(
                normalized_keyword_name, None
            )
            if found_in_cache is not None:
                return found_in_cache

            from robotframework_ls.impl.text_utilities import (
                matches_name_with_variables,
            )

            for keyword_name_used in self._keywords_used:
                if matches_name_with_variables(
                    keyword_name_used, normalized_keyword_name
                ):
                    ret = True
                    break

            self._check_name_with_vars_cache_usage[normalized_keyword_name] = ret
        return ret

    def has_global_variable_definition(self, normalized_variable_name: str) -> bool:
        return normalized_variable_name in self._global_variables_defined

    def has_variable_reference(self, normalized_variable_name: str) -> bool:
        return normalized_variable_name in self._variable_references

    def get_json_list(self) -> List[ISymbolsJsonListEntry]:
        return self._json_list

    def get_library_info(self) -> Optional[ILibraryDoc]:
        w = self._library_info
        if w is None:
            return None
        return w()

    def get_doc(self) -> Optional[IRobotDocument]:
        w = self._doc
        if w is None:
            return None
        return w()

    def iter_keyword_info(self) -> Iterator[ISymbolKeywordInfo]:
        raise NotImplementedError("iter_keyword_info abstract in: %s", self.__class__)


class SymbolsCacheReverseIndex:
    def __init__(self):
        self._global_var_to_uris: Dict[str, Set[str]] = {}

        self._lock = threading.Lock()
        self._reindex_count = 0

        self._uris_changed = set()
        self._force_reindex = True

    def request_full_reindex(self):
        with self._lock:
            self._force_reindex = True
            self._uris_changed.clear()

    def notify_uri_changed(self, uri: str) -> None:
        with self._lock:
            if not self._force_reindex:
                self._uris_changed.add(uri)
                if len(self._uris_changed) > 1:
                    self._force_reindex = True
                    self._uris_changed.clear()

    def has_global_variable(self, normalized_var_name: str) -> bool:
        return normalized_var_name in self._global_var_to_uris

    def get_global_variable_uri_definitions(
        self, normalized_var_name: str
    ) -> Optional[Set[str]]:
        return self._global_var_to_uris.get(normalized_var_name)

    def synchronize(self, context: ICompletionContext):
        with self._lock:
            if not self._force_reindex:
                if not self._uris_changed or self._uris_changed == {context.doc.uri}:
                    # If the only thing changed is the current uri (or if there
                    # were no changes), don't do a workspace-wide update.
                    return

            # Reset synchronize-related flags.
            self._force_reindex = False
            self._uris_changed.clear()

            self._reindex_count += 1
            self._compute_new_symbols_cache_reverse_index_state(context)

    def dispose(self):
        self._global_var_to_uris = {}

    def _compute_new_symbols_cache_reverse_index_state(
        self, context: ICompletionContext
    ) -> None:
        from robotframework_ls.impl.workspace_symbols import iter_symbols_caches

        new_global_var_to_uris: Dict[str, Set[str]] = {}
        symbols_cache: BaseSymbolsCache

        # Note: always update as a whole.
        it = typing.cast(Iterator[BaseSymbolsCache], iter_symbols_caches("", context))

        try:
            for symbols_cache in it:
                uri = symbols_cache.get_uri()
                if not uri:
                    continue

                for global_var_name in symbols_cache._global_variables_defined:
                    s = new_global_var_to_uris.get(global_var_name)
                    if s is None:
                        s = new_global_var_to_uris[global_var_name] = set()
                    s.add(uri)
        except:
            log.exception("Exception computing symbols cache reverse index.")
            raise  # Maybe it was cancelled (or we had another error).
        else:
            # ok, it worked, let's actually update our internal state.
            self._global_var_to_uris = new_global_var_to_uris
