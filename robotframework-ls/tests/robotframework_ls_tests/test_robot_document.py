def test_get_ast():
    from robotframework_ls.impl.robot_workspace import RobotDocument

    d = RobotDocument(uri="unkwown", source="*** Settings ***")
    ast = d.get_ast()
    assert ast is not None
    assert d.get_ast() is ast  # Check cache

    d.source = "*** Foobar"
    assert d.get_ast() is not ast


def test_document_from_file(workspace, workspace_dir, cases):
    from os.path import os
    from robocorp_ls_core import uris
    from robocorp_ls_core.lsp import TextDocumentItem

    cases.copy_to("case1", workspace_dir)
    workspace.set_root(workspace_dir)

    ws = workspace.ws
    case1_file = os.path.join(workspace_dir, "case1.robot")
    assert os.path.exists(case1_file)

    case1_doc_uri = uris.from_fs_path(case1_file)
    resource_doc = ws.get_document(case1_doc_uri, accept_from_file=False)
    assert resource_doc is None

    cached_doc = ws.get_document(case1_doc_uri, accept_from_file=True)
    assert cached_doc is not None
    assert "*** Settings ***" in cached_doc.source

    with open(case1_file, "w") as stream:
        stream.write("new contents")
    assert "*** Settings ***" in cached_doc.source  # i.e.: Unchanged

    # When we get it again it verifies the filesystem.
    cached_doc2 = ws.get_document(case1_doc_uri, accept_from_file=True)
    assert cached_doc is cached_doc2
    assert cached_doc.source == "new contents"

    # Still None if we can't accept cached.
    resource_doc = ws.get_document(case1_doc_uri, accept_from_file=False)
    assert resource_doc is None

    ws.put_document(TextDocumentItem(case1_doc_uri, text="rara"))
    resource_doc = ws.get_document(case1_doc_uri, accept_from_file=False)
    assert resource_doc is not None
    assert resource_doc is not cached_doc

    ws.remove_document(case1_doc_uri)
    resource_doc = ws.get_document(case1_doc_uri, accept_from_file=False)
    assert resource_doc is None
    cached_doc3 = ws.get_document(case1_doc_uri, accept_from_file=True)
    assert cached_doc3 is not None

    # i.e.: it should've been pruned when the doc was added.
    assert cached_doc3 is not cached_doc
    assert cached_doc3.source == "new contents"

    os.remove(case1_file)
    cached_doc4 = ws.get_document(case1_doc_uri, accept_from_file=True)
    assert cached_doc4 is None

    # The old one in memory doesn't change after the file is removed
    assert cached_doc3.source == "new contents"
