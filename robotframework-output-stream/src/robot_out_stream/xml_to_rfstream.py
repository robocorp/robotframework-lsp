import xml.sax.handler
import sys
import datetime
from typing import Optional, Callable


class _RobotData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None

    def __str__(self):
        return f"_RobotData"

    __repr__ = __str__


class _SuiteData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None

    def __str__(self):
        return f'_SuiteData({self.attrs.get("name")})'

    __repr__ = __str__


class _TestData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None
        self.tags = []
        self.sent = False

    def __str__(self):
        return f'_TestData({self.attrs.get("name")})'

    __repr__ = __str__


class _AbstractKeywordData:
    def __init__(self, attrs):
        self.attrs = attrs
        self.status = None

        self.args = []

        self.doc = ""
        self.sent = False

    @property
    def name(self):
        raise NotImplementedError

    @property
    def type(self):
        raise NotImplementedError


class _KeywordData(_AbstractKeywordData):
    def __init__(self, attrs):
        _AbstractKeywordData.__init__(self, attrs)
        self.var_assign = []

    @property
    def name(self):
        return self.attrs.get("name")

    @property
    def type(self):
        return "KEYWORD"

    def __str__(self):
        return f"_KeywordData({self.name})"

    __repr__ = __str__


class _ForData(_AbstractKeywordData):
    def __init__(self, attrs):
        _AbstractKeywordData.__init__(self, attrs)
        self.var = "<unset>"
        self.values = []

    @property
    def flavor(self):
        return self.attrs.get("flavor", "<unknown-flavor>")

    @property
    def type(self):
        return "FOR"

    @property
    def name(self):
        return f"{self.var} {self.flavor} [{' | '.join(self.values)}]"

    def __str__(self):
        return f"_ForData({self.name})"

    __repr__ = __str__


class _ReturnData(_AbstractKeywordData):
    def __init__(self, attrs):
        _AbstractKeywordData.__init__(self, attrs)
        self.values = []

    @property
    def type(self):
        return "RETURN"

    @property
    def name(self):
        return f"{' | '.join(self.values)}"

    def __str__(self):
        return f"_ReturnData({self.name})"

    __repr__ = __str__


class _WhileData(_AbstractKeywordData):
    def __init__(self, attrs):
        _AbstractKeywordData.__init__(self, attrs)
        self.condition = attrs.get("condition", "<unknown condition>")

    @property
    def type(self):
        return "WHILE"

    @property
    def name(self):
        return f"{self.condition}"

    def __str__(self):
        return f"_WhileData({self.name})"

    __repr__ = __str__


class _BranchData(_AbstractKeywordData):
    """
    Branch data can be:
    - if/else if/else
    - try/except/finally
    """

    def __init__(self, attrs):
        _AbstractKeywordData.__init__(self, attrs)
        self.condition = attrs.get("condition")  # Used on if/else if
        self.pattern = None  # Used on except (message)

    @property
    def type(self):
        return self.attrs.get("type")

    @property
    def name(self):
        if self.condition:
            return self.condition
        if self.pattern:
            return self.pattern
        return ""

    def __str__(self):
        return f"_BranchData({self.name})"

    __repr__ = __str__


class _IterData(_AbstractKeywordData):
    def __init__(self, attrs):
        _AbstractKeywordData.__init__(self, attrs)
        self.var_name = None
        self.var = None

    @property
    def type(self):
        return "ITERATION"

    @property
    def name(self):
        if self.var_name is not None and self.var is not None:
            return f"{self.var_name} = {self.var}"
        if self.var_name is not None:
            return f"{self.var_name}"
        if self.var is not None:
            return f"{self.var}"
        return ""

    def __str__(self):
        return f"_IterData({self.name})"

    __repr__ = __str__


def compute_timedelta(initial_time: datetime.datetime, endtime_str: str):
    endtime: datetime.datetime = parse_time(endtime_str)
    delta = endtime - initial_time
    return round(delta.total_seconds(), 3)


class _Status:
    def __init__(self, attrs):
        self.attrs = attrs

    @property
    def status(self):
        return self.attrs["status"]

    @property
    def endtime(self):
        return self.attrs["endtime"]

    @property
    def starttime(self):
        return self.attrs["starttime"]

    def compute_start_timedelta(self, initial_time):
        return compute_timedelta(initial_time, self.starttime)

    def compute_end_timedelta(self, initial_time):
        return compute_timedelta(initial_time, self.endtime)


class _XmlSaxParser(xml.sax.handler.ContentHandler):
    """
    Notes:

    - Log messages are unscoped (they just appear as errors in the
      end and thus we can't know what was the current keyword).

    - The start/end time is written as the last thing in the
      element along with the status, so, we have a special message
      to write the start (in general the protocol would send it along
      with the test time, but we send it afterwards so that we can
      use the sax parser).
    """

    def __init__(self, create_listener):
        self._create_listener = create_listener
        self._listener = None
        self._stack = []
        self._need_chars = False
        self._chars = []
        self._curr_message_attrs = None
        self._found_logs = set()

    def startElement(self, name, attrs):
        method = getattr(self, "start_" + name, None)
        if method:
            try:
                method(attrs)
            except:
                raise RuntimeError(
                    f"Error when starting element: {name}. Attrs: {attrs}. Stack: {self._stack}"
                )
        # else:
        #     print("Unhandled start:", name)

    def endElement(self, name):
        method = getattr(self, "end_" + name, None)
        if method:
            try:
                method()
            except:
                raise RuntimeError(
                    f"Error when finishing element: {name}. Stack: {self._stack}"
                )
        # else:
        #     print("Unhandled end:", name)

    def start_robot(self, attrs):
        assert self._listener is None
        generator = attrs.get("generator")
        self._listener = self._create_listener(attrs)
        self._listener.send_info(generator)
        self._stack.append(_RobotData(attrs))

    def end_robot(self):
        self.send_delayed()
        del self._stack[-1]

    def start_suite(self, attrs):
        self.send_delayed()
        name = attrs.get("name")
        suiteid = attrs.get("id")
        source = attrs.get("source")
        if name and suiteid:
            self._stack.append(_SuiteData(attrs))
            self._listener.start_suite(
                name, {"id": suiteid, "source": source, "timedelta": -1}
            )
        else:
            self._stack.append(None)

    def end_suite(self):
        self.send_delayed()
        s = self._stack.pop(-1)
        if s is not None:
            status = s.status.attrs["status"]
            self._listener.send_start_time_delta(
                s.status.compute_start_timedelta(self._listener.initial_time)
            )

            self._listener.end_suite(
                s.attrs["name"], {"status": status, "timedelta": -1}
            )

    def start_test(self, attrs):
        self.send_delayed()
        name = attrs.get("name")
        suiteid = attrs.get("id")
        if name and suiteid:
            self._stack.append(_TestData(attrs))
        else:
            self._stack.append(None)

    def end_test(self):
        self.send_delayed()
        s = self._stack.pop(-1)
        if s is not None:
            status = s.status.status

            self._listener.send_start_time_delta(
                s.status.compute_start_timedelta(self._listener.initial_time)
            )

            self._listener.end_test(
                s.attrs["name"],
                {
                    "status": status,
                    "timedelta": s.status.compute_end_timedelta(
                        self._listener.initial_time
                    ),
                    "message": "",
                },
            )

    def start_kw(self, attrs):
        self.send_delayed()
        name = attrs.get("name")
        if name:
            self._stack.append(_KeywordData(attrs))

            # We can't send it right away because we need the args which will
            # just appear afterwards...
        else:
            self._stack.append(None)

    def send_delayed(self):
        if not self._stack:
            return

        peek = self._stack[-1]
        if not hasattr(peek, "sent"):
            return

        if not peek.sent:
            if isinstance(peek, _AbstractKeywordData):
                peek.sent = True
                attrs = peek.attrs
                name = peek.name
                libname = attrs.get("library", "")
                doc = peek.doc
                args = peek.args
                assign = getattr(peek, "var_assign", [])
                self._listener.start_keyword(
                    name,
                    {
                        "kwname": name,
                        "libname": libname,
                        "doc": doc,
                        "args": args,
                        "type": peek.type,
                        "timedelta": -1,
                        "assign": assign,
                        "source": None,  # source is never available in this case.
                        "lineno": -1,
                    },
                )
            elif isinstance(peek, _TestData):
                peek.sent = True

                attrs = peek.attrs
                name = attrs.get("name")
                suiteid = attrs.get("id")
                line = attrs.get("line")
                tags = peek.tags

                self._listener.start_test(
                    name, {"id": suiteid, "lineno": line, "timedelta": -1, "tags": tags}
                )

    def end_kw(self):
        self.send_delayed()
        s = self._stack.pop(-1)
        if s is not None:
            status = s.status.status

            self._listener.send_start_time_delta(
                s.status.compute_start_timedelta(self._listener.initial_time)
            )
            self._listener.end_keyword(
                s.name,
                {
                    "status": status,
                    "timedelta": s.status.compute_end_timedelta(
                        self._listener.initial_time
                    ),
                    "message": "",
                },
            )

    def _get_chars_and_disable(self):
        self._need_chars = False
        content = "".join(self._chars)
        self._chars = []
        return content

    def start_for(self, attrs):
        self.send_delayed()
        self._stack.append(_ForData(attrs))

    end_for = end_kw

    def start_return(self, attrs):
        self.send_delayed()
        self._stack.append(_ReturnData(attrs))

    end_return = end_kw

    def start_branch(self, attrs):
        self.send_delayed()
        self._stack.append(_BranchData(attrs))

    end_branch = end_kw

    def start_while(self, attrs):
        self.send_delayed()
        self._stack.append(_WhileData(attrs))

    end_while = end_kw

    def start_iter(self, attrs):
        self.send_delayed()
        self._stack.append(_IterData(attrs))

    end_iter = end_kw

    def start_var(self, attrs):
        self._need_chars = True
        data = self._stack[-1]
        if hasattr(data, "var_name"):
            data.var_name = attrs.get("name")

    def end_var(self):
        content = self._get_chars_and_disable()
        data = self._stack[-1]
        if hasattr(data, "var_assign"):
            data.var_assign.append(content)
        else:
            data.var = content

    def start_value(self, attrs):
        self._need_chars = True

    def end_value(self):
        content = self._get_chars_and_disable()
        data = self._stack[-1]
        data.values.append(content)

    def start_pattern(self, attrs):
        self._need_chars = True

    def end_pattern(self):
        content = self._get_chars_and_disable()
        data = self._stack[-1]
        if isinstance(data, _BranchData):
            data.pattern = content

    def start_arg(self, attrs):
        self._need_chars = True

    def end_arg(self):
        content = self._get_chars_and_disable()
        if self._stack:
            peek = self._stack[-1]
            if isinstance(peek, _AbstractKeywordData):
                peek.args.append(content)

    def start_tag(self, attrs):
        self._need_chars = True

    def end_tag(self):
        content = self._get_chars_and_disable()
        if self._stack:
            peek = self._stack[-1]
            if isinstance(peek, _TestData):
                if not peek.sent:
                    peek.tags.append(content)
                else:
                    # The test data was already sent (it can be sent
                    # just at the end, which isn't ideal...).
                    self.send_delayed()
                    self._listener.send_tag(content)

    def start_doc(self, attrs):
        self._need_chars = True

    def end_doc(self):
        content = self._get_chars_and_disable()
        if self._stack:
            peek = self._stack[-1]
            if isinstance(peek, _AbstractKeywordData):
                peek.doc = content

    def start_msg(self, attrs):
        # <msg timestamp="20221024 15:23:26.952" level="INFO">Some &lt;data &amp;encode &lt;/script&gt;</msg>
        self._need_chars = True
        self._curr_message_attrs = attrs

    def end_msg(self):
        self.send_delayed()
        content = self._get_chars_and_disable()

        level = self._curr_message_attrs["level"]
        timestamp = self._curr_message_attrs["timestamp"]
        html = self._curr_message_attrs.get("html")

        self._chars = []
        self._curr_message_attrs = None

        key = (level, content, timestamp)
        if key in self._found_logs:
            # RF duplicates messages at the end of the log. We just
            # want to show it once.
            return
        self._found_logs.add(key)

        self._listener.log_message(
            {
                "level": level,
                "message": content,
                "html": html,
                "timedelta": compute_timedelta(self._listener.initial_time, timestamp),
            }
        )

    def characters(self, content):
        if self._need_chars:
            self._chars.append(content)

    def start_status(self, attrs):
        self.send_delayed()
        if self._stack:
            self._stack[-1].status = _Status(attrs)

    def end_status(self):
        pass  # no-op


def parse_time(date_str):
    return datetime.datetime.strptime(date_str, "%Y%m%d %H:%M:%S.%f")


def convert_xml_to_rfstream(source, write: Optional[Callable[[str], None]] = None):
    """
    :param source:
        Either a string pointing to the path to be parsed or some stream-like
        object with the contents.

    :param write:
        A callable to be used to write the contents received (sent line-by-line).
    """
    from robot_out_stream import RFStream

    if write is None:

        def write(s):
            sys.stdout.write(s)

    def create_listener(robot_attrs):
        initial_date_str = robot_attrs["generated"]
        initial_time = parse_time(initial_date_str)
        kwargs = dict(
            __write__=write,
            __initial_time__=initial_time,
            __additional_info__=[f"Generated from output.xml"],
            __uuid__="gen-from-output-xml",
        )
        kwargs["--dir"] = "None"
        listener = RFStream(**kwargs)
        return listener

    xml.sax.parse(source, _XmlSaxParser(create_listener))
