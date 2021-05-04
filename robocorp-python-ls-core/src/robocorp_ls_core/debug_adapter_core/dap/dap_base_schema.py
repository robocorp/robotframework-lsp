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
import json
import itertools
from functools import partial
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class BaseSchema(object):
    type: str
    seq: int

    @staticmethod
    def initialize_ids_translation():
        BaseSchema._dap_id_to_obj_id = {0: 0, None: None}
        BaseSchema._obj_id_to_dap_id = {0: 0, None: None}
        BaseSchema._next_dap_id = partial(next, itertools.count(1))

    def to_json(self, update_ids_to_dap=False):
        return json.dumps(self.to_dict(update_ids_to_dap=update_ids_to_dap))

    def to_dict(self, update_ids_to_dap=False) -> dict:
        raise NotImplementedError("Must be overridden.")

    @staticmethod
    def _translate_id_to_dap(obj_id):
        if obj_id == "*":
            return "*"
        # Note: we don't invalidate ids, so, if some object starts using the same id
        # of another object, the same id will be used.
        dap_id = BaseSchema._obj_id_to_dap_id.get(obj_id)
        if dap_id is None:
            dap_id = BaseSchema._obj_id_to_dap_id[obj_id] = BaseSchema._next_dap_id()
            BaseSchema._dap_id_to_obj_id[dap_id] = obj_id
        return dap_id

    @staticmethod
    def _translate_id_from_dap(dap_id):
        if dap_id == "*":
            return "*"
        try:
            return BaseSchema._dap_id_to_obj_id[dap_id]
        except:
            raise KeyError("Wrong ID sent from the client: %s" % (dap_id,))

    @staticmethod
    def update_dict_ids_to_dap(dct):
        return dct

    @staticmethod
    def update_dict_ids_from_dap(dct):
        return dct


BaseSchema.initialize_ids_translation()

_requests_to_types = {}
_responses_to_types = {}
_event_to_types = {}
_all_messages = {}


def register(cls):
    _all_messages[cls.__name__] = cls
    return cls


def register_request(command):
    def do_register(cls):
        _requests_to_types[command] = cls
        return cls

    return do_register


def register_response(command):
    def do_register(cls):
        _responses_to_types[command] = cls
        return cls

    return do_register


def register_event(event):
    def do_register(cls):
        _event_to_types[event] = cls
        return cls

    return do_register


def from_dict(dct, update_ids_from_dap=False, cls=None):
    msg_type = dct.get("type")
    if msg_type is None:
        raise ValueError("Unable to make sense of message: %s" % (dct,))

    if cls is None:
        if msg_type == "request":
            to_type = _requests_to_types
            use = dct["command"]

        elif msg_type == "response":
            to_type = _responses_to_types
            use = dct["command"]

        else:
            to_type = _event_to_types
            use = dct["event"]

        cls = to_type.get(use)

    if cls is None:
        raise ValueError(
            "Unable to create message from dict: %s. %s not in %s"
            % (dct, use, sorted(to_type.keys()))
        )
    try:
        return cls(update_ids_from_dap=update_ids_from_dap, **dct)
    except:
        msg = "Error creating %s from %s" % (cls, dct)
        log.exception(msg)
        raise


def from_json(json_msg, update_ids_from_dap=False, on_dict_loaded=lambda dct: None):
    if isinstance(json_msg, bytes):
        json_msg = json_msg.decode("utf-8")

    as_dict = json.loads(json_msg)
    on_dict_loaded(as_dict)
    try:
        return from_dict(as_dict, update_ids_from_dap=update_ids_from_dap)
    except:
        if as_dict.get("type") == "response" and not as_dict.get("success"):
            # Error messages may not have required body (return as a generic Response).
            Response = _all_messages["Response"]
            return Response(**as_dict)
        else:
            raise


def get_response_class(request):
    if request.__class__ == dict:
        return _responses_to_types[request["command"]]
    return _responses_to_types[request.command]


def build_response(request, kwargs=None):
    if kwargs is None:
        kwargs = {"success": True}
    else:
        if "success" not in kwargs:
            kwargs["success"] = True
    response_class = _responses_to_types[request.command]
    kwargs.setdefault("seq", -1)  # To be overwritten before sending
    return response_class(command=request.command, request_seq=request.seq, **kwargs)
