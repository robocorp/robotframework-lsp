from robocorp.actions import action


@action
def my_action() -> str:
    return "result"


@action(is_consequential=False)
def my_action_2() -> str:
    return "result"
