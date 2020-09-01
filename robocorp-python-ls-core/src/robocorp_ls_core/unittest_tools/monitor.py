import sys
import threading
import traceback


def dump_threads():
    thread_id_to_name = {}
    try:
        for t in threading.enumerate():
            thread_id_to_name[t.ident] = "%s  (daemon: %s)" % (t.name, t.daemon)
    except:
        pass

    stack_trace = [
        "===============================================================================",
        "Threads still found running after tests finished",
        "================================= Thread Dump =================================",
    ]

    for thread_id, stack in sys._current_frames().items():
        stack_trace.append(
            "\n-------------------------------------------------------------------------------"
        )
        stack_trace.append(" Thread %s" % thread_id_to_name.get(thread_id, thread_id))
        stack_trace.append("")

        if "self" in stack.f_locals:
            sys.stderr.write(str(stack.f_locals["self"]) + "\n")

        for filename, lineno, name, line in traceback.extract_stack(stack):
            stack_trace.append(' File "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                stack_trace.append("   %s" % (line.strip()))
    stack_trace.append(
        "\n=============================== END Thread Dump ==============================="
    )
    sys.stderr.write("\n".join(stack_trace))
