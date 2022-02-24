from typing import Optional, Set, List
import weakref

from robocorp_ls_core.protocols import ITestInfoFromSymbolsCacheTypedDict
from robotframework_ls.impl.protocols import (
    ILibraryDoc,
    IRobotDocument,
    ISymbolsJsonListEntry,
)


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
    ):
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
        self._test_info = test_info

    def get_test_info(self) -> Optional[List[ITestInfoFromSymbolsCacheTypedDict]]:
        return self._test_info

    def get_uri(self) -> Optional[str]:
        return self._uri

    def has_keyword_usage(self, normalized_keyword_name: str) -> bool:
        return normalized_keyword_name in self._keywords_used

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
