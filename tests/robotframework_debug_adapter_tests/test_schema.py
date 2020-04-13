# Original work Copyright Fabio Zadrozny (EPL 1.0)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

def test_schema():
    from robotframework_debug_adapter.dap import dap_base_schema
    from robotframework_debug_adapter.dap.dap_schema import (
        InitializeRequest,
        InitializeRequestArguments,
        InitializeResponse,
        Capabilities,
        InitializedEvent,
    )

    json_msg = """
{
    "arguments": {
        "adapterID": "PyDev", 
        "clientID": "vscode", 
        "clientName": "Visual Studio Code", 
        "columnsStartAt1": true, 
        "linesStartAt1": true, 
        "locale": "en-us", 
        "pathFormat": "path", 
        "supportsRunInTerminalRequest": true, 
        "supportsVariablePaging": true, 
        "supportsVariableType": true
    }, 
    "command": "initialize", 
    "seq": 1, 
    "type": "request"
}"""

    initialize_request = dap_base_schema.from_json(json_msg)
    assert initialize_request.__class__ == InitializeRequest
    assert initialize_request.arguments.__class__ == InitializeRequestArguments
    assert initialize_request.arguments.adapterID == "PyDev"
    assert initialize_request.command == "initialize"
    assert initialize_request.type == "request"
    assert initialize_request.seq == 1

    response = dap_base_schema.build_response(initialize_request)
    assert response.__class__ == InitializeResponse
    assert response.seq == -1  # Must be set before sending
    assert response.command == "initialize"
    assert response.type == "response"
    assert response.body.__class__ == Capabilities

    assert response.to_dict() == {
        "seq": -1,
        "type": "response",
        "request_seq": 1,
        "success": True,
        "command": "initialize",
        "body": {},
    }

    capabilities = response.body  # : :type capabilities: Capabilities
    capabilities.supportsCompletionsRequest = True
    assert response.to_dict() == {
        "seq": -1,
        "type": "response",
        "request_seq": 1,
        "success": True,
        "command": "initialize",
        "body": {"supportsCompletionsRequest": True},
    }

    initialize_event = InitializedEvent()
    assert initialize_event.to_dict() == {
        "seq": -1,
        "type": "event",
        "event": "initialized",
    }
