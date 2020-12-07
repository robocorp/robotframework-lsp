def test_locators():
    from robocorp_code.locators.locator_webdriver import Webdriver
    from robocorp_code.protocols import ActionResult

    w = Webdriver()
    w.start()
    w.navigate("http://google.com")

    # i.e.: Uncomment to manually click the element instead of hard-coding
    # value.
    # action_result = w.pick_as_dict_info()
    # assert action_result.result
    # print(action_result.result)
    dct = {
        "strategy": "name",
        "value": "q",
        "source": "https://www.google.com/?gws_rd=ssl",
        "screenshot": "iVBORw0KGgoAAAANSUhEUgAAAb8AAAAiCAYAAADPnNdbAAAAAXNSR0IArs4c6QAAAJ1JREFUeJzt1TEBACAMwDDAv+fhAo4mCvp1z8wsAAg5vwMA4DXzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgJwLXQ0EQMJRx4AAAAAASUVORK5CYII=",
    }
    action_result = ActionResult(True, None, dct)
    assert action_result.result["value"] == "q"
    assert action_result.result["strategy"] == "name"
    result = w.validate_dict_info(action_result.result)
    if not result.result:
        raise AssertionError(result.message)
    w.stop()
