import * as path from "path";
import * as fs from "fs";
import {
    window,
    commands,
    WorkspaceFolder,
    DebugAdapterExecutable,
    debug,
    DebugConfiguration,
    DebugConfigurationProvider,
    CancellationToken,
    extensions,
} from "vscode";
import * as roboConfig from "./robocorpSettings";
import { OUTPUT_CHANNEL } from "./channel";
import { resolveInterpreter } from "./activities";
import {
    ROBOCORP_COMPUTE_ROBOT_LAUNCH_FROM_ROBOCORP_CODE_LAUNCH,
    ROBOCORP_UPDATE_LAUNCH_ENV,
    ROBOCORP_GET_CONNECTED_VAULT_WORKSPACE_INTERNAL,
} from "./robocorpCommands";
import { globalCachedPythonInfo } from "./extension";

interface ActionResult {
    success: boolean;
    message: string;
    result: any;
}

export class RobocorpCodeDebugConfigurationProvider implements DebugConfigurationProvider {
    provideDebugConfigurations?(folder: WorkspaceFolder | undefined, token?: CancellationToken): DebugConfiguration[] {
        let configurations: DebugConfiguration[] = [];
        configurations.push({
            "type": "robocorp-code",
            "name": "Robocorp Code: Launch task from robot.yaml",
            "request": "launch",
            "robot": '^"\\${file}"',
            "task": "",
        });
        return configurations;
    }

    async resolveDebugConfigurationWithSubstitutedVariables(
        folder: WorkspaceFolder | undefined,
        debugConfiguration: DebugConfiguration,
        token?: CancellationToken
    ): Promise<DebugConfiguration> {
        if (!fs.existsSync(debugConfiguration.robot)) {
            window.showWarningMessage('Error. Expected: specified "robot": ' + debugConfiguration.robot + " to exist.");
            return;
        }

        let interpreter: InterpreterInfo | undefined = undefined;
        let interpreterResult = await resolveInterpreter(debugConfiguration.robot);
        if (!interpreterResult.success) {
            window.showWarningMessage("Error resolving interpreter info: " + interpreterResult.message);
            return;
        }
        interpreter = interpreterResult.result;
        if (!interpreter) {
            window.showWarningMessage("Unable to resolve interpreter for: " + debugConfiguration.robot);
            return;
        }

        if (!interpreter.environ) {
            window.showErrorMessage("Unable to resolve interpreter environment based on: " + debugConfiguration.robot);
            return;
        }

        // Resolve environment
        let env = interpreter.environ;
        try {
            let newEnv: { [key: string]: string } | "cancelled" = await commands.executeCommand(
                ROBOCORP_UPDATE_LAUNCH_ENV,
                {
                    "targetRobot": debugConfiguration.robot,
                    "env": env,
                }
            );
            if (newEnv === "cancelled") {
                OUTPUT_CHANNEL.appendLine("Launch cancelled");
                return;
            } else {
                env = newEnv;
            }
        } catch (error) {
            // The command may not be available.
        }

        if (debugConfiguration.noDebug) {
            let vaultInfoActionResult: ActionResult = await commands.executeCommand(
                ROBOCORP_GET_CONNECTED_VAULT_WORKSPACE_INTERNAL
            );
            if (vaultInfoActionResult?.success && vaultInfoActionResult.result) {
                debugConfiguration.workspaceId = vaultInfoActionResult.result.workspaceId;
            }
            // Not running with debug: just use rcc to launch.
            debugConfiguration.env = env;
            return debugConfiguration;
        }
        // If it's a debug run, we need to get the input contents -- something as:
        // "type": "robocorp-code",
        // "name": "Robocorp Code: Launch task from current robot.yaml",
        // "request": "launch",
        // "robot": "c:/robot.yaml",
        // "task": "entrypoint",
        //
        // and convert it to the contents expected by robotframework-lsp:
        //
        // "type": "robotframework-lsp",
        // "name": "Robot: Current File",
        // "request": "launch",
        // "cwd": "${workspaceFolder}",
        // "target": "c:/task.robot",
        //
        // (making sure that we can actually do this and it's a robot launch for the task)

        let actionResult: ActionResult = await commands.executeCommand(
            ROBOCORP_COMPUTE_ROBOT_LAUNCH_FROM_ROBOCORP_CODE_LAUNCH,
            {
                "name": debugConfiguration.name,
                "request": debugConfiguration.request,
                "robot": debugConfiguration.robot,
                "task": debugConfiguration.task,
                "additionalPythonpathEntries": interpreter.additionalPythonpathEntries,
                "env": env,
                "pythonExe": interpreter.pythonExe,
            }
        );

        if (!actionResult.success) {
            window.showErrorMessage(actionResult.message);
            return;
        }
        let result = actionResult.result;
        if (result && result.type && result.type == "python") {
            let extension = extensions.getExtension("ms-python.python");
            if (extension) {
                if (!extension.isActive) {
                    // i.e.: Auto-activate python extension for the launch as the extension
                    // is only activated for debug on the resolution, whereas in this case
                    // the launch is already resolved.
                    await extension.activate();
                }
            }
        }

        // OUTPUT_CHANNEL.appendLine("Launching with: " + JSON.stringify(result));

        return result;
    }
}

export function registerDebugger() {
    async function createDebugAdapterExecutable(config: DebugConfiguration): Promise<DebugAdapterExecutable> {
        let env = config.env;
        if (!env) {
            env = {};
        }
        let robotHome = roboConfig.getHome();
        if (robotHome && robotHome.length > 0) {
            if (env) {
                env["ROBOCORP_HOME"] = robotHome;
            } else {
                env = { "ROBOCORP_HOME": robotHome };
            }
        }
        let targetMain: string = path.resolve(__dirname, "../../src/robocorp_code_debug_adapter/__main__.py");
        if (!fs.existsSync(targetMain)) {
            window.showWarningMessage("Error. Expected: " + targetMain + " to exist.");
            return;
        }

        if (!globalCachedPythonInfo) {
            window.showWarningMessage("Error. Expected globalCachedPythonInfo to be set when launching debugger.");
            return;
        }
        const pythonExecutable = globalCachedPythonInfo.pythonExe;
        if (!fs.existsSync(pythonExecutable)) {
            window.showWarningMessage("Error. Expected: " + pythonExecutable + " to exist.");
            return;
        }

        if (env) {
            return new DebugAdapterExecutable(pythonExecutable, ["-u", targetMain], { "env": env });
        } else {
            return new DebugAdapterExecutable(pythonExecutable, ["-u", targetMain]);
        }
    }

    debug.registerDebugAdapterDescriptorFactory("robocorp-code", {
        createDebugAdapterDescriptor: (session) => {
            const config: DebugConfiguration = session.configuration;
            return createDebugAdapterExecutable(config);
        },
    });

    debug.registerDebugConfigurationProvider("robocorp-code", new RobocorpCodeDebugConfigurationProvider());
}
