from typing import Optional
from robotframework_ls.impl.protocols import IRobotDocument
from robocorp_ls_core import uris


class CompletionContextWorkspaceCaches:
    def on_file_changed(self, filename: str):
        """
        Called when a file is changed in the file-system (i.e.: it was saved).
        """
        if filename and filename.endswith((".resource", ".robot")):
            uri = uris.from_fs_path(filename)

    def on_updated_document(self, uri: str, document: Optional[IRobotDocument]):
        """
        Called when a document was updated in-memory.
        :param uri:
            The uri for the document that was just updated.
        :param document:
            The document just updated or None if it was removed.
        """

    def clear_caches(self):
        """
        Called when all caches should be cleared.
        """

    def dispose(self):
        pass
