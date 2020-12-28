class Setting(object):
    def __init__(
        self,
        name,
        default,
        description,
        setting_type=["string", "null"],
        enum=None,
        js_type=None,
        add_to_json=True,
    ):
        """
        :param name:
        :param default:
        :param description:
        :param setting_type:
            Can be something as 'string', 'array', 'number', 'boolean'.
        :param enum:
            If it must be a predefined value, this can be a list with the values
            i.e.: ['alpha','bravo','charlie']
        :param js_type:
            If it's an array of strings, this should be something as string[]
        """
        self.name = name
        self.default = default
        self.description = description
        self.setting_type = setting_type
        self.enum = enum
        self.js_type = js_type
        self.add_to_json = add_to_json


SETTINGS = [
    Setting(
        "robocorp.language-server.tcp-port",
        0,
        "If the port is specified, connect to the language server previously started at the given port. Requires a VSCode restart to take effect.",
        setting_type="number",
    ),
    Setting(
        "robocorp.language-server.args",
        [],
        'Specifies the arguments to be passed to the Robocorp Code language server (i.e.: ["-vv", "--log-file=~/robocorp_code.log"]). Requires a VSCode restart to take effect.',
        setting_type="array",
        js_type="string[]",
    ),
    Setting(
        "robocorp.language-server.python",
        "",
        "Specifies the path to the python executable to be used for the Robocorp Code Language Server (the default is searching python on the PATH). Requires a VSCode restart to take effect.",
        setting_type="string",
    ),
    Setting(
        "robocorp.rcc.location",
        "",
        "Specifies the location of the rcc tool.",
        setting_type="string",
    ),
    Setting(
        "robocorp.rcc.endpoint",
        "",
        "Can be used to specify a different endpoint for rcc.",
        setting_type="string",
    ),
    Setting(
        "robocorp.rcc.config_location",
        "",
        "Specifies the config location used by rcc.",
        setting_type="string",
    ),
    Setting(
        "robocorp.home",
        "",
        "Specifies the value for ROBOCORP_HOME (where the conda environments will be downloaded). Must point to a directory without spaces in it.",
        setting_type="string",
    ),
    Setting(
        "robocorp.verifyLSP",
        "true",
        "Verify if the Robot Framework Language Server is installed?",
        setting_type="boolean",
    ),
]


def get_settings_for_json():
    settings_contributed = {}
    for setting in SETTINGS:
        if not setting.add_to_json:
            continue
        dct = {
            "type": setting.setting_type,
            "default": setting.default,
            "description": setting.description,
        }
        if setting.enum:
            dct["enum"] = setting.enum
        settings_contributed[setting.name] = dct
    return settings_contributed
