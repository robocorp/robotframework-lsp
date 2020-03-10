# To generate libspec:
# python -m robot.libdoc --format xml my_library my_library.libspec
# To run:
# set PYTHONPATH=.
# robot case1.robot


def verify_model(model):
    print("verifying model:", model)


def verify_another_model(model):
    print("verifying another model:", model)
