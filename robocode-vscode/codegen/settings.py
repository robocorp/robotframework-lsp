class Setting(object):
    def __init__(
        self,
        name,
        default,
        description,
        setting_type=["string", "null"],
        enum=None,
        js_type=None,
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


SETTINGS = [
    Setting(
        "robocode.language-server.tcp-port",
        0,
        "If the port is specified, connect to the language server previously started at the given port. Requires a VSCode restart to take effect.",
        setting_type="number",
    ),
    Setting(
        "robocode.language-server.args",
        [],
        'Specifies the arguments to be passed to the Robocode language server (i.e.: ["-vv", "--log-file=~/robocode_vscode.log"]). Requires a VSCode restart to take effect.',
        setting_type="array",
        js_type="string[]",
    ),
    Setting(
        "robocode.language-server.python",
        "",
        "Specifies the path to the python executable to be used for the Robocode Language Server (the default is searching python on the PATH). Requires a VSCode restart to take effect.",
        setting_type="string",
    ),
]


def get_settings_for_json():
    settings_contributed = {}
    for setting in SETTINGS:
        dct = {
            "type": setting.setting_type,
            "default": setting.default,
            "description": setting.description,
        }
        if setting.enum:
            dct["enum"] = setting.enum
        settings_contributed[setting.name] = dct
    return settings_contributed
