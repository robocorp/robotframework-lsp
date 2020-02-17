class Options(object):

    tcp = False
    host = "127.0.0.1"
    port = 1456
    log_file = None
    verbose = 0


class Setup(object):

    # After parsing args it's replaced with the actual setup.
    options = Options


# Note: set to False only when debugging.
USE_TIMEOUTS = True

NO_TIMEOUT = None
