# To generate libspec:
# python -m robot.libdoc --format xml case1_library case1_library.libspec
# To run:
# set PYTHONPATH=.
# robot case1.robot
from enum import Enum


class SomeEnum(Enum):
    v1 = 0
    v2 = 1


def simple_arg(model):
    """
    Some doc in simple_arg.
    """


def arg_with_type(model: int):
    """
    Some doc in arg_with_type.
    """


def arg_with_enum_type(model: SomeEnum):
    pass


def arg_with_enum_type_and_default(model: SomeEnum = SomeEnum.v2):
    pass


def arg_with_starargs(arg1, arg2=10, *arg3, **arg4):
    pass


def arg_with_default_empty_arg(arg1, arg2=""):
    pass


def arg_with_default_none_arg(arg1, arg2=None):
    pass


def arg_with_positional(arg1, *, arg2):
    pass


def arg_string_default(arg1="my:,my:something,*foo,**foo,<rara>"):
    pass
