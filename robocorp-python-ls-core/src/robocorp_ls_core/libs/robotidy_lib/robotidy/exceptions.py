class RobotidyConfigError(Exception):
    pass


class InvalidParameterValueError(RobotidyConfigError):
    def __init__(self, transformer, param, value, msg):
        exc_msg = f"{transformer}: Invalid '{param}' parameter value: '{value}'. {msg}"
        super().__init__(exc_msg)


class InvalidParameterError(RobotidyConfigError):
    def __init__(self, transformer, similar):
        super().__init__(
            f"{transformer}: Failed to import. Verify if correct name or configuration was provided.{similar}"
        )


class InvalidParameterFormatError(RobotidyConfigError):
    def __init__(self, transformer):
        super().__init__(
            f"{transformer}: Invalid parameter format. Pass parameters using MyTransformer:param_name=value syntax."
        )


class ImportTransformerError(RobotidyConfigError):
    pass
