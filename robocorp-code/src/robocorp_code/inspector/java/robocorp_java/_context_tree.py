import queue
import threading

from JABWrapper.context_tree import ContextTree
from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper


class ContextTreeThread(threading.Thread):
    """
    Building the ContextTree in a big java application may take several minutes.
    """

    def __init__(self, jab_wrapper: JavaAccessBridgeWrapper):
        super().__init__()
        self._queue = queue.Queue()
        self._jab_wrapper = jab_wrapper

    def run(self) -> None:
        context_tree = ContextTree(self._jab_wrapper)
        self._queue.put(context_tree)

    def get_context_tree(self) -> ContextTree:
        return self._queue.get()
