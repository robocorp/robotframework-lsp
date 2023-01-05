from functools import partial
from typing import List, Optional

from robocorp_ls_core.basic import log_and_silence_errors
from robocorp_ls_core.jsonrpc.endpoint import require_monitor
from robocorp_ls_core.protocols import (
    IRobotFrameworkApiClient,
    IMonitor,
    IIdMessageMatcher,
)
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.lsp import CompletionItemTypedDict


log = get_logger(__name__)


class _RobotFrameworkLsCompletionImpl(object):
    def __init__(self, server_manager, language_server):
        import weakref

        self._weak_robot_framework_ls = weakref.ref(language_server)
        self._server_manager = server_manager

        self._last_stored = {}

    def text_document_completion(self, doc_uri: str, line: int, col: int):
        rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        if rf_api_client is not None:
            func = partial(
                self._threaded_document_completion,
                rf_api_client,
                doc_uri,
                line,
                col,
            )
            func = require_monitor(func)
            return func

        log.info("Unable to get completions (no api available).")
        return []

    @log_and_silence_errors(log, return_on_error=[])
    def _threaded_document_completion(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        doc_uri: str,
        line: int,
        col: int,
        monitor: IMonitor,
    ) -> list:
        from robocorp_ls_core.client_base import wait_for_message_matchers
        from robotframework_ls.ls_timeouts import get_timeout
        from robotframework_ls.ls_timeouts import TimeoutReason

        ls = self._weak_robot_framework_ls()
        if not ls:
            log.critical("RobotFrameworkLanguageServer garbage-collected.")
            return []

        ws = ls.workspace
        if not ws:
            log.critical("Workspace must be set before returning completions.")
            return []

        document = ws.get_document(doc_uri, accept_from_file=True)
        if document is None:
            log.critical("Unable to find document (%s) for completions." % (doc_uri,))
            return []

        config = ls.config
        completions_timeout = get_timeout(config, TimeoutReason.completion)

        completions = []

        # Asynchronous completion.
        message_matchers: List[Optional[IIdMessageMatcher]] = []
        message_matchers.append(rf_api_client.request_complete_all(doc_uri, line, col))

        accepted_message_matchers = wait_for_message_matchers(
            message_matchers,
            monitor,
            rf_api_client.request_cancel,
            completions_timeout,
        )
        for message_matcher in accepted_message_matchers:
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    for completion_item in result:
                        data = completion_item.get("data")
                        if data and isinstance(data, dict):
                            # We need to add the doc uri to the data.
                            data["uri"] = doc_uri
                        completions.append(completion_item)

        return completions

    def resolve_completion_item(self, completion_item: CompletionItemTypedDict):
        try:
            data = completion_item.get("data")
            if data and isinstance(data, dict):
                doc_uri = data.get("uri")
                ls = self._weak_robot_framework_ls()
                if not ls:
                    log.critical(
                        "RobotFrameworkLanguageServer garbage-collected in resolve completion item."
                    )
                    return completion_item

                return ls.async_api_forward(
                    "request_resolve_completion_item",
                    "api",
                    doc_uri,
                    default_return=completion_item,
                    __add_doc_uri_in_args__=False,
                    completion_item=completion_item,
                )
        except:
            log.exception("Error resolving completion item.")

        return completion_item
