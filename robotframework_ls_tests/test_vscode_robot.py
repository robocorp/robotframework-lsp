def test_diagnostics(language_server, ws_root_path, data_regression):
    language_server.initialize(ws_root_path)

    language_server.write(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "untitled:Untitled-1",
                    "languageId": "robotframework",
                    "version": 1,
                    "text": "",
                }
            },
        }
    )

    language_server.write(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "untitled:Untitled-1", "version": 2},
                "contentChanges": [
                    {
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 0, "character": 0},
                        },
                        "rangeLength": 0,
                        "text": "*** Invalid Invalid ***",
                    }
                ],
            },
        }
    )

    diag = language_server.wait_for_message(
        {"method": "textDocument/publishDiagnostics"}
    )

    data_regression.check(diag, basename="diagnostics")
