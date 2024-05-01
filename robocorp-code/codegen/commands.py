from convert import convert_case_to_constant


class Command(object):
    def __init__(
        self,
        name,
        title,
        add_to_package_json=True,
        keybinding="",
        server_handled=True,
        icon=None,  # https://microsoft.github.io/vscode-codicons/dist/codicon.html
        enablement=None,
        hide_from_command_palette=False,
        constant="",
        when_clause=None,
    ):
        """
        :param add_to_package_json:
            If a command should not appear to the user, add_to_package_json should be False.
        :param server_handled:
            If True this is a command handled in the server (and not in the client) and
            thus will be registered as such.
        :param constant:
            If given the internal constant used will be this one (used when a command
            is renamed and we want to keep compatibility).
        """
        self.name = name
        self.title = title
        self.add_to_package_json = add_to_package_json
        self.keybinding = keybinding
        self.server_handled = server_handled
        self.icon = icon
        self.enablement = enablement

        if hide_from_command_palette:
            assert (
                not when_clause
            ), "hide_from_command_palette and when_clause may not be both specified."
            when_clause = "false"

        self.when_clause = when_clause

        if not constant:
            constant = convert_case_to_constant(name)
        self.constant = constant


COMMANDS = [
    Command(
        "robocorp.getLanguageServerPython",
        "Get a python executable suitable to start the language server",
        add_to_package_json=False,
        server_handled=False,
    ),
    Command(
        "robocorp.getLanguageServerPythonInfo",
        "Get info suitable to start the language server {pythonExe, environ}",
        add_to_package_json=False,
        server_handled=False,
    ),
    Command(
        "robocorp.getPluginsDir",
        "Get the directory for plugins",
        add_to_package_json=False,
        server_handled=True,
    ),
    # Note: this command is started from the client (due to needing window.showQuickPick)
    # and the proceeds to ask for the server for the actual implementation.
    Command(
        "robocorp.createRobot",
        "Create Task Package (Robot)",
        server_handled=False,
        icon="$(add)",
    ),
    Command(
        "robocorp.createActionPackage",
        "Create Action Package",
        server_handled=False,
        icon="$(add)",
    ),
    Command(
        "robocorp.createTaskOrActionPackage",
        "Create Action Package",
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(add)",
    ),
    # Internal commands for robocorp.createRobot.
    Command(
        "robocorp.listRobotTemplates.internal",
        "Provides a list with the available Task Package (Robot) templates",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.createRobot.internal",
        "Actually calls rcc to create the Task Package (Robot)",
        add_to_package_json=False,
        server_handled=True,
    ),
    # Started from the client due to needing UI actions.
    Command(
        "robocorp.uploadRobotToCloud",
        "Upload Task Package (Robot) to Control Room",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.localListRobots.internal",
        "Lists the activities currently available in the workspace",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.isLoginNeeded.internal",
        "Checks if the user is already linked to an account",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.getLinkedAccountInfo.internal",
        "Provides information related to the current linked account",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudLogin",
        "Link to Control Room",
        add_to_package_json=True,
        server_handled=False,
        icon="$(link)",
    ),
    Command(
        "robocorp.cloudLogin.internal",
        "Link to Control Room (receives credentials)",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudListWorkspaces.internal",
        "Lists the workspaces available for the user (in the Control Room)",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.uploadToNewRobot.internal",
        "Uploads a Task Package (Robot) as a new Task Package (Robot) in the Control Room",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.uploadToExistingRobot.internal",
        "Uploads a Task Package (Robot) as an existing Task Package (Robot) in the Control Room",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.runInRcc.internal",
        "Runs a custom command in RCC",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.runRobotRcc",
        "Run Task Package (Robot)",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.runActionFromActionPackage",
        "Run Action (from Action Package)",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.debugRobotRcc",
        "Debug Task Package (Robot)",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.debugActionFromActionPackage",
        "Debug Action (from Action Package)",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.robotsViewTaskRun",
        "Launch Task",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon={"light": "images/light/run.svg", "dark": "images/dark/run.svg"},
    ),
    Command(
        "robocorp.robotsViewTaskDebug",
        "Debug Task",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon={"light": "images/light/debug.svg", "dark": "images/dark/debug.svg"},
    ),
    Command(
        "robocorp.robotsViewActionRun",
        "Launch Action",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon={"light": "images/light/run.svg", "dark": "images/dark/run.svg"},
    ),
    Command(
        "robocorp.robotsViewActionDebug",
        "Debug Action",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon={"light": "images/light/debug.svg", "dark": "images/dark/debug.svg"},
    ),
    Command(
        "robocorp.robotsViewActionEditInput",
        "Configure Action Input",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(symbol-variable)",
    ),
    Command(
        "robocorp.robotsViewActionOpen",
        "Open Action",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(go-to-file)",
    ),
    Command(
        "robocorp.runRobocorpsPythonTask",
        "Run Robocorp's Python Task",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon={"light": "images/light/run.svg", "dark": "images/dark/run.svg"},
    ),
    Command(
        "robocorp.debugRobocorpsPythonTask",
        "Debug Robocorp's Python Task",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon={"light": "images/light/debug.svg", "dark": "images/dark/debug.svg"},
    ),
    Command(
        "robocorp.saveInDiskLRU",
        "Saves some data in an LRU in the disk",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.loadFromDiskLRU",
        "Loads some LRU data from the disk",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.computeRobotLaunchFromRobocorpCodeLaunch",
        "Computes a Task Package (Robot) launch debug configuration based on the robocorp code launch debug configuration",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.setPythonInterpreter",
        "Set python executable based on robot.yaml",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.resolveInterpreter",
        "Resolves the interpreter to be used given a path",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.cloudLogout",
        "Unlink and remove credentials from Control Room",
        add_to_package_json=True,
        server_handled=False,
        icon="$(debug-disconnect)",
    ),
    Command(
        "robocorp.cloudLogout.internal",
        "Unlink and remove credentials from Control Room internal",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.refreshRobotsView",
        "Refresh Task Packages (Robots) view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
    ),
    Command(
        "robocorp.refreshRobotContentView",
        "Refresh Task Package (Robot) Content view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.newFileInRobotContentView",
        "New File",
        add_to_package_json=True,
        server_handled=False,
        icon="$(new-file)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.newFolderInRobotContentView",
        "New Folder",
        add_to_package_json=True,
        server_handled=False,
        icon="$(new-folder)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.deleteResourceInRobotContentView",
        "Delete",
        add_to_package_json=True,
        server_handled=False,
        icon="$(close)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.renameResourceInRobotContentView",
        "Rename",
        add_to_package_json=True,
        server_handled=False,
        icon="$(edit)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.refreshCloudView",
        "Refresh Robocorp view",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/refresh.svg", "dark": "images/dark/refresh.svg"},
    ),
    Command(
        "robocorp.getLocatorsJsonInfo",
        "Obtain information from the locators.json given a robot.yaml",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.removeLocatorFromJson.internal",
        "Remove a named locator from locators.json",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.removeLocatorFromJson",
        "Remove Locator",
        add_to_package_json=True,
        hide_from_command_palette=True,
        server_handled=False,
        icon="$(trash)",
    ),
    Command(
        "robocorp.openLocatorsJson",
        "Open locators.json",
        add_to_package_json=True,
        hide_from_command_palette=True,
        server_handled=False,
        icon="$(go-to-file)",
    ),
    Command(
        "robocorp.openCloudHome",
        "Open cloud home",
        add_to_package_json=True,
        hide_from_command_palette=True,
        server_handled=False,
        icon="$(cloud)",
    ),
    # This is the same as the one above, but it won't ask what's the robot, it'll
    # just use the one selected in the robots tree.
    Command(
        "robocorp.newRobocorpInspectorBrowser",
        "Add Web Locator",
        add_to_package_json=True,
        server_handled=False,
        icon="$(add)",
    ),
    Command(
        "robocorp.newRobocorpInspectorWindows",
        "Add Windows Locator",
        add_to_package_json=True,
        server_handled=False,
        icon="$(add)",
    ),
    Command(
        "robocorp.newRobocorpInspectorImage",
        "Add Image Locator",
        add_to_package_json=True,
        server_handled=False,
        icon="$(add)",
    ),
    Command(
        "robocorp.newRobocorpInspectorJava",
        "Add Java Locator",
        add_to_package_json=True,
        server_handled=False,
        icon="$(add)",
    ),
    Command(
        "robocorp.openPlaywrightRecorder",
        "Open Playwright Recorder",
        add_to_package_json=True,
        server_handled=False,
        icon={"light": "images/light/run.svg", "dark": "images/dark/run.svg"},
    ),
    Command(
        "robocorp.openPlaywrightRecorder.internal",
        "Open Playwright Recorder Internal",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
        icon={"light": "images/light/run.svg", "dark": "images/dark/run.svg"},
    ),
    Command(
        "robocorp.editRobocorpInspectorLocator",
        "Edit locator",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(edit)",
    ),
    Command(
        "robocorp.copyLocatorToClipboard.internal",
        "Copy locator name to clipboard",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(clippy)",
    ),
    Command(
        "robocorp.openRobotTreeSelection",
        "Configure Task Package (Robot) (robot.yaml)",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(go-to-file)",
    ),
    Command(
        "robocorp.openRobotCondaTreeSelection",
        "Configure Dependencies (conda.yaml)",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(list-tree)",
    ),
    Command(
        "robocorp.openPackageYamlTreeSelection",
        "Configure Action Package (package.yaml)",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(list-tree)",
    ),
    Command(
        "robocorp.openExternally",
        "Open externally",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(go-to-file)",
    ),
    Command(
        "robocorp.openInVSCode",
        "Open in VSCode",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(file)",
    ),
    Command(
        "robocorp.revealInExplorer",
        "Reveal in File Explorer",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(file-submodule)",
    ),
    Command(
        "robocorp.revealRobotInExplorer",
        "Reveal robot.yaml in File Explorer",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(file-submodule)",
    ),
    Command(
        "robocorp.cloudUploadRobotTreeSelection",
        "Upload Task Package (Robot) to Control Room",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(cloud-upload)",
    ),
    Command(
        "robocorp.rccTerminalCreateRobotTreeSelection",
        "Open terminal with Package Python environment",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=False,
        icon="$(terminal)",
        constant="ROBOCORP_CREATE_RCC_TERMINAL_TREE_SELECTION",
    ),
    Command(
        "robocorp.sendMetric",
        "Send metric",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.submitIssue.internal",
        "Submit issue (internal)",
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command("robocorp.submitIssue", "Submit issue to Robocorp", server_handled=False),
    Command(
        "robocorp.inspector.internal",
        "Inspector Manager (internal)",
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.inspector",
        "Open Inspector",
        server_handled=False,
        hide_from_command_palette=False,
    ),
    Command(
        "robocorp.inspector.duplicate",
        "Create & manage locators",
        server_handled=False,
        hide_from_command_palette=False,
    ),
    Command(
        "robocorp.errorFeedback.internal",
        "Error feedback (internal)",
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.feedback.internal",
        "Feedback (internal)",
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.configuration.diagnostics.internal",
        "Task Package (Robot) Configuration Diagnostics (internal)",
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.configuration.diagnostics",
        "Task Package (Robot) Configuration Diagnostics",
        server_handled=False,
    ),
    Command(
        "robocorp.rccTerminalNew",
        "Terminal with Task Package (Robot) environment",
        server_handled=False,
        icon="$(terminal)",
    ),
    Command(
        "robocorp.listWorkItems.internal",
        "Lists the work items available for a Task Package (Robot)",
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.updateLaunchEnv",
        "Updates the environment variables used for some launch (given a Task Package (Robot))",
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.updateLaunchEnv.getVaultEnv.internal",
        "Provides the environment variables related to the vault.",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.newWorkItemInWorkItemsView",
        "New Work Item",
        add_to_package_json=True,
        server_handled=False,
        icon="$(add)",
        hide_from_command_palette=False,
    ),
    Command(
        "robocorp.deleteWorkItemInWorkItemsView",
        "Delete Work Item",
        add_to_package_json=True,
        server_handled=False,
        icon="$(trash)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.helpWorkItems",
        "Work Items Help",
        add_to_package_json=True,
        server_handled=False,
        icon="$(question)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.convertOutputWorkItemToInput",
        "Convert output work item to input",
        add_to_package_json=True,
        server_handled=False,
        icon="$(fold-up)",
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.verifyLibraryVersion.internal",
        "Collect a library version and verify if it matches some expected version",
        add_to_package_json=False,
        server_handled=True,
    ),
    Command(
        "robocorp.connectWorkspace",
        "Connect to Control Room Workspace (vault, storage, ...)",
        icon="$(lock)",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.disconnectWorkspace",
        "Disconnect from Control Room Workspace",
        icon="$(unlock)",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.getConnectedVaultWorkspace.internal",
        "Gets workspace id currently connected",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.setConnectedVaultWorkspace.internal",
        "Sets the currently connected Control Room Workspace",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.openVaultHelp",
        "Open vault help",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.clearEnvAndRestart",
        "Clear Robocorp (RCC) environments and restart Robocorp Code",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.showOutput",
        "Show Robocorp Code > Output logs",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.showInterpreterEnvError",
        "Show error related to interpreter env creation",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.openFlowExplorerTreeSelection",
        "Open Flow Explorer",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=True,
        icon="$(type-hierarchy-sub)",
    ),
    Command(
        "robocorp.convertProject",
        "Conversion Accelerator from third party RPA to Robocorp Task Package (Robot)",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=False,
    ),
    Command(
        "robocorp.profileImport",
        "Import Profile",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=False,
        icon="$(file-symlink-file)",
    ),
    Command(
        "robocorp.profileImport.internal",
        "Import Profile (internal)",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.profileSwitch",
        "Switch Profile",
        add_to_package_json=True,
        server_handled=False,
        hide_from_command_palette=False,
        icon="$(git-pull-request)",
    ),
    Command(
        "robocorp.profileSwitch.internal",
        "Switch Profile",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.profileList.internal",
        "List Profiles",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.hasPreRunScripts.internal",
        "Has Pre Run Scripts",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.runPreRunScripts.internal",
        "Run Pre Run Scripts",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.getPyPiBaseUrls.internal",
        "Get PyPi base urls",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.startActionServer",
        "Start Action Server",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.downloadActionServer",
        "Download Action Server",
        add_to_package_json=True,
        server_handled=False,
    ),
    Command(
        "robocorp.startActionServer.internal",
        "Start Action Server (internal)",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.listActions.internal",
        "Lists the actions available in an action package given a root dir (internal)",
        add_to_package_json=True,
        server_handled=True,
        hide_from_command_palette=True,
    ),
    Command(
        "robocorp.packageEnvironmentRebuild",
        "Rebuild Package Environment",
        server_handled=False,
        hide_from_command_palette=False,
    ),
]


def get_keybindings_for_json():
    keybinds_contributed = []
    for command in COMMANDS:
        if not command.add_to_package_json:
            continue

        if command.keybinding:
            keybinds_contributed.append(
                {
                    "key": command.keybinding,
                    "command": command.name,
                    "when": "editorTextFocus",
                }
            )

    return keybinds_contributed


def get_commands_for_json():
    commands_contributed = []
    for command in COMMANDS:
        if not command.add_to_package_json:
            continue
        dct = {"command": command.name, "title": command.title, "category": "Robocorp"}
        if command.icon:
            dct["icon"] = command.icon
        if command.enablement:
            dct["enablement"] = command.enablement
        commands_contributed.append(dct)

    return commands_contributed


def get_activation_events_for_json():
    activation_events = []
    for command in COMMANDS:
        activation_events.append("onCommand:" + command.name)

    activation_events.append("onDebugInitialConfigurations")
    activation_events.append("onDebugResolve:robocorp-code")

    return activation_events
