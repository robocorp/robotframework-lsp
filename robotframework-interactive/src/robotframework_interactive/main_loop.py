class MainLoopCallbackHolder:
    ON_MAIN_LOOP = None


def interpreter_main_loop():
    MainLoopCallbackHolder.ON_MAIN_LOOP()
