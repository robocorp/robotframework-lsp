from typing import Optional, Hashable, TypeVar, Generic, Iterator, Tuple, Set
from robotframework_ls.impl.protocols import (
    IRobotDocument,
    ICompletionContextWorkspaceCaches,
    ICompletionContextDependencyGraph,
    IOnDependencyChanged,
)
from robocorp_ls_core import uris
from collections import OrderedDict
import threading
from robotframework_ls.impl.robot_constants import (
    ROBOT_AND_TXT_FILE_EXTENSIONS,
    LIBRARY_FILE_EXTENSIONS,
    VARIABLE_FILE_EXTENSIONS,
)
from contextlib import contextmanager
from robocorp_ls_core.options import BaseOptions
from robocorp_ls_core.robotframework_log import get_logger
import json

T = TypeVar("T")

log = get_logger(__name__)


class _LRU(Generic[T]):
    """
    A really-simple LRU to help us keep track of only a few dependency graphs.
    """

    def __init__(self, max_size: int):
        self._cache: "OrderedDict[Hashable, T]" = OrderedDict()
        self._max_size = max_size

    def get(self, key: Hashable) -> Optional[T]:
        val = self._cache.get(key)
        if val is None:
            return None
        else:
            self._cache.move_to_end(key)
            return val

    def put(self, key: Hashable, value: T) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def pop(self, key: Hashable, default: Optional[T] = None) -> Optional[T]:
        return self._cache.pop(key, default)

    def clear(self) -> None:
        self._cache.clear()

    def items(self) -> Iterator[Tuple[Hashable, T]]:
        yield from self._cache.items()

    def values(self) -> Iterator[T]:
        yield from self._cache.values()


class _InvalidationTracker:
    def __init__(self):
        self._uris_invalidated = set()
        self._all_invalidated = False

    def mark_uri_invalidated(self, uri):
        self._uris_invalidated.add(uri)

    def mark_all_invalidated(self):
        self._all_invalidated = True

    def is_dependency_graph_still_valid(self, dependency_graph) -> bool:
        if self._all_invalidated:
            return False
        for uri in self._uris_invalidated:
            if dependency_graph.do_invalidate_on_uri_change(uri):
                return False

        return True


class CompletionContextWorkspaceCaches:
    def __init__(
        self, on_dependency_changed: Optional[IOnDependencyChanged] = None
    ) -> None:
        self._lock = threading.Lock()
        # Small cache because invalidation could become slow in a big cache
        # (and it should be enough to hold what we're currently working with).
        self._cached: _LRU[ICompletionContextDependencyGraph] = _LRU(5)
        self.cache_hits = 0
        self.invalidations = 0

        self._invalidation_trackers: Set[_InvalidationTracker] = set()
        self._on_dependency_changed = on_dependency_changed

    def _invalidate_uri(self, uri: str) -> None:
        with self._lock:
            notified = set()
            for invalidation_tracker in self._invalidation_trackers:
                invalidation_tracker.mark_uri_invalidated(uri)

            did_invalidate_entry = False

            for key, entry in tuple(self._cached.items()):
                if entry.do_invalidate_on_uri_change(uri):
                    uri = entry.get_root_doc().uri
                    if uri not in notified:
                        notified.add(uri)
                        if self._on_dependency_changed:
                            self._on_dependency_changed(uri)

                    did_invalidate_entry = True
                    invalidated: Optional[
                        ICompletionContextDependencyGraph
                    ] = self._cached.pop(key, None)
                    if BaseOptions.DEBUG_CACHE_DEPS and invalidated:
                        log.info(
                            "Invalidated: %s\n%s\n",
                            key,
                            json.dumps(invalidated.to_dict(), indent=4),
                        )

            if BaseOptions.DEBUG_CACHE_DEPS and not did_invalidate_entry:
                log.info("%s did not invalidate the caches:", uri)
                for key, entry in tuple(self._cached.items()):
                    log.info(
                        json.dumps(entry.to_dict(), indent=4),
                    )

    @contextmanager
    def invalidation_tracker(self):
        try:
            with self._lock:
                invalidation_tracker = _InvalidationTracker()
                self._invalidation_trackers.add(invalidation_tracker)

            yield invalidation_tracker

        finally:
            with self._lock:
                self._invalidation_trackers.discard(invalidation_tracker)

    def on_file_changed(self, filename: str):
        """
        Called when a file is changed in the file-system (i.e.: it was saved).
        """
        if filename:
            lower = filename.lower()
            if lower.endswith(ROBOT_AND_TXT_FILE_EXTENSIONS):
                uri = uris.from_fs_path(filename)
                self._invalidate_uri(uri)

            elif lower.endswith(LIBRARY_FILE_EXTENSIONS):
                # If a library changes, we consider all caches invalid because
                # we don't hold an association to know which library maps to
                # which files at this level.
                self.clear_caches()

            elif lower.endswith(VARIABLE_FILE_EXTENSIONS):
                self.clear_caches()

    def on_updated_document(self, uri: str, document: Optional[IRobotDocument]):
        """
        Called when a (robot) document was updated in-memory.
        :param uri:
            The uri for the document that was just updated.
        :param document:
            The document just updated or None if it was removed.
        """
        self._invalidate_uri(uri)

    def clear_caches(self):
        """
        Called when all caches should be cleared.
        """
        with self._lock:
            self.invalidations += 1
            for invalidation_tracker in self._invalidation_trackers:
                invalidation_tracker.mark_all_invalidated()
            self._cached.clear()

    def dispose(self):
        self.clear_caches()

    def get_cached_dependency_graph(
        self, cache_key: Hashable
    ) -> Optional[ICompletionContextDependencyGraph]:
        with self._lock:
            ret = self._cached.get(cache_key)
            if ret is not None:
                self.cache_hits += 1

            if BaseOptions.DEBUG_CACHE_DEPS:
                if ret is not None:
                    log.info(
                        "Cache HIT (%s):\n%s\n",
                        cache_key,
                        json.dumps(ret.to_dict(), indent=4),
                    )
                else:
                    log.info(
                        "Cache MISS (%s):\n%s\n",
                        cache_key,
                        "  \n".join(
                            json.dumps(x.to_dict(), indent=4)
                            for x in self._cached.values()
                        ),
                    )

            return ret

    def cache_dependency_graph(
        self,
        cache_key: Hashable,
        dependency_graph: ICompletionContextDependencyGraph,
        invalidation_tracker: _InvalidationTracker,
    ) -> None:
        with self._lock:
            if invalidation_tracker.is_dependency_graph_still_valid(dependency_graph):
                self._cached.put(cache_key, dependency_graph)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ICompletionContextWorkspaceCaches = check_implements(self)
