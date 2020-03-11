# To generate libspec:
# python -m robot.libdoc --format xml case1_library case1_library.libspec
# To run:
# set PYTHONPATH=.
# robot case1.robot


def verify_model(model):
    """
    :type model: int
    """
    print("verifying model:", model)


def verify_another_model(model):
    print("verifying another model:", model)
