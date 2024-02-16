from robocorp.actions import action


@action
def my_action() -> str:
    return "result"
