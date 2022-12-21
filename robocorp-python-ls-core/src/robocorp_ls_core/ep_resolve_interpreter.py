"""
This is done to solve the use-case where we can (potentially) have a different
interpreter for different directories.

i.e.:

Given some structure as:

/env1
    /robot.yaml <- specifies libraries needed and additional pythonpath entries.
    /robot1.robot
/env2
    /robot.yaml
    /robot2.robot
    
We want to use the info on robot.yaml in env1 to say that a given set of
libraries is needed, whereas the robot.yaml in env2 has another set of 
libraries (and each will have a different virtual environment managing it).

Note that this implementation logic is not really builtin, rather, an external
contributor needs to add the extension point to do that.

The usage of the extension point should do something as:

    interpreter_info = ep.get_interpreter_info_for_doc_uri(doc_uri) 
    if interpreter_info is not None:
        interpreter_info.get_interpreter_id()
        interpreter_info.get_python_exe()
        interpreter_info.get_environ()
        
Later, it can decide to get rid of some server which handles a given python
executable if there's no interpreter id using a given python executable anymore.

Note: to add an extension, one needs to add it through a plugin using the 
"robot.addPluginsDir" command.
"""

from typing import Optional, List, Dict
import sys

# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

else:
    from typing import Protocol


class IInterpreterInfo(Protocol):
    def get_interpreter_id(self) -> str:
        """
        This is an identification and should relate to the place which allows
        to identify this info (it should usually be given by some location --
        for instance, it could be identified by the robot.yaml location).

        Note that different interpreter ids can point to the same python
        executable (if they'd have the same robot.yaml contents).
        """

    def get_python_exe(self) -> str:
        """
        The python executable that should be used.
        """

    def get_environ(self) -> Optional[Dict[str, str]]:
        """
        The environment to be used.
        """

    def get_additional_pythonpath_entries(self) -> List[str]:
        """
        Any additional PYTHONPATH entries to be considered.
        """


class EPResolveInterpreter(Protocol):
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        """
        Provides a customized interpreter for a given document uri.
        """


class DefaultInterpreterInfo(object):
    """
    A Default implementation for the interpreter info where everything is
    pre-computed.
    """

    def __init__(
        self,
        interpreter_id: str,
        python_exe: str,
        environ: Optional[Dict[str, str]],
        additional_pythonpath_entries: List[str],
    ) -> None:
        self.interpreter_id = interpreter_id
        self.python_exe = python_exe
        self.environ = environ
        self.additional_pythonpath_entries = additional_pythonpath_entries

    def get_interpreter_id(self) -> str:
        return self.interpreter_id

    def get_python_exe(self) -> str:
        return self.python_exe

    def get_environ(self) -> Optional[Dict[str, str]]:
        return self.environ

    def get_additional_pythonpath_entries(self) -> List[str]:
        return self.additional_pythonpath_entries

    def __str__(self):
        return f"DefaultInterpreterInfo({self.interpreter_id}, {self.python_exe})"

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IInterpreterInfo = check_implements(self)
