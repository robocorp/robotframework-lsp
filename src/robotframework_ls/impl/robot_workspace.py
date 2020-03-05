from robotframework_ls.workspace import Workspace, Document


class RobotWorkspace(Workspace):
    def _create_document(self, doc_uri, source=None, version=None):
        return RobotDocument(doc_uri, source, version)


class RobotDocument(Document):
    pass  # TODO: store ast in document
