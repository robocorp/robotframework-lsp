def _read_into_queue(reader, queue):
    def _put_into_queue(msg):
        queue.put(msg)

    reader.listen(_put_into_queue)


class _LanguageServerClient(object):
    def __init__(self, writer, reader):
        import threading

        try:
            from queue import Queue
        except:
            from Queue import Queue

        self.writer = writer
        self.reader = reader
        self._queue = Queue()

        t = threading.Thread(target=_read_into_queue, args=(reader, self._queue))
        t.start()

    def write(self, contents):
        self.writer.write(contents)

    def next_message(self):
        return self._queue.get(block=True, timeout=5)

    def wait_for_message(self, match):
        found = False
        while not found:
            msg = self.next_message()
            for key, value in match.items():
                if msg.get(key) == value:
                    continue
                break
            else:
                found = True
        return msg

    def initialize(self, root_path, msg_id=0):
        from robotframework_ls.uris import from_fs_path

        self.write(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {
                    "processId": 18724,
                    "rootPath": root_path,
                    "rootUri": from_fs_path(root_path),
                    "capabilities": {
                        "workspace": {
                            "applyEdit": True,
                            "didChangeConfiguration": {"dynamicRegistration": True},
                            "didChangeWatchedFiles": {"dynamicRegistration": True},
                            "symbol": {"dynamicRegistration": True},
                            "executeCommand": {"dynamicRegistration": True},
                        },
                        "textDocument": {
                            "synchronization": {
                                "dynamicRegistration": True,
                                "willSave": True,
                                "willSaveWaitUntil": True,
                                "didSave": True,
                            },
                            "completion": {
                                "dynamicRegistration": True,
                                "completionItem": {
                                    "snippetSupport": True,
                                    "commitCharactersSupport": True,
                                },
                            },
                            "hover": {"dynamicRegistration": True},
                            "signatureHelp": {"dynamicRegistration": True},
                            "definition": {"dynamicRegistration": True},
                            "references": {"dynamicRegistration": True},
                            "documentHighlight": {"dynamicRegistration": True},
                            "documentSymbol": {"dynamicRegistration": True},
                            "codeAction": {"dynamicRegistration": True},
                            "codeLens": {"dynamicRegistration": True},
                            "formatting": {"dynamicRegistration": True},
                            "rangeFormatting": {"dynamicRegistration": True},
                            "onTypeFormatting": {"dynamicRegistration": True},
                            "rename": {"dynamicRegistration": True},
                            "documentLink": {"dynamicRegistration": True},
                        },
                    },
                    "trace": "off",
                },
            }
        )

        self.wait_for_message({"id": msg_id})
