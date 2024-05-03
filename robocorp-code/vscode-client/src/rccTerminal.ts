import { Progress, ProgressLocation, window } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import * as pathModule from "path";
import { listAndAskRobotSelection, resolveInterpreter } from "./activities";
import { getRccLocation } from "./rcc";
import { mergeEnviron } from "./subprocess";
import { getAutosetpythonextensiondisableactivateterminal } from "./robocorpSettings";
import { disablePythonTerminalActivateEnvironment } from "./pythonExtIntegration";
import { LocalRobotMetadataInfo, ActionResult, InterpreterInfo } from "./protocols";
import * as fsModule from "fs";

export async function askAndCreateRccTerminal() {
    let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
        "Please select the target Task Package for the terminal.",
        "Unable to create terminal (no Task Package detected in the Workspace).",
        { showActionPackages: true, showTaskPackages: true }
    );
    if (robot) {
        await createRccTerminal(robot);
    }
}

export async function createRccTerminal(robotInfo: LocalRobotMetadataInfo) {
    if (robotInfo) {
        async function startShell(progress: Progress<{ message?: string; increment?: number }>): Promise<undefined> {
            const rccLocation = await getRccLocation();
            if (!rccLocation) {
                OUTPUT_CHANNEL.appendLine(
                    "Unable to collect environment to create terminal with RCC:" +
                        rccLocation +
                        " for Package: " +
                        robotInfo.name
                );
                window.showErrorMessage("Unable to find RCC.");
                return;
            }

            let result: ActionResult<InterpreterInfo | undefined> = await resolveInterpreter(robotInfo.filePath);
            if (!result.success) {
                window.showWarningMessage("Error resolving interpreter info: " + result.message);
                return;
            }

            let interpreter: InterpreterInfo = result.result;
            if (!interpreter || !interpreter.pythonExe) {
                window.showWarningMessage("Unable to obtain interpreter information from: " + robotInfo.filePath);
                return;
            }
            OUTPUT_CHANNEL.appendLine("Retrieved Python interpreter: " + interpreter.pythonExe);

            // If vscode-python is installed, we need to disable the terminal activation as it
            // conflicts with the robot environment.
            if (getAutosetpythonextensiondisableactivateterminal()) {
                await disablePythonTerminalActivateEnvironment();
            }

            let env = mergeEnviron();
            // Update env to contain rcc location.
            if (interpreter.environ) {
                for (let key of Object.keys(interpreter.environ)) {
                    let value = interpreter.environ[key];
                    let isPath = false;
                    if (process.platform == "win32") {
                        key = key.toUpperCase();
                        if (key == "PATH") {
                            isPath = true;
                        }
                    } else {
                        if (key == "PATH") {
                            isPath = true;
                        }
                    }
                    if (isPath) {
                        value = pathModule.dirname(rccLocation) + pathModule.delimiter + value;
                    }

                    env[key] = value;
                }
            }
            OUTPUT_CHANNEL.appendLine("Retrieved environment: " + JSON.stringify(env, null, 2));

            OUTPUT_CHANNEL.appendLine(
                "Create terminal with RCC: " + rccLocation + " for Package: " + robotInfo.filePath
            );

            // We need to activate the RCC python environment after the terminal has spawned
            // This way we avoid the environment being overwritten by shell startup scripts
            // The Terminal env injection works if no overwrites happen
            if (process.platform.toString() === "win32") {
                // Making sure we create a CMD prompt in Windows as it can default to PowerShell
                // and the Python Environment activation fails
                const terminal = window.createTerminal({
                    name: robotInfo.name + " Package environment",
                    env: env,
                    cwd: pathModule.dirname(robotInfo.filePath),
                    message: "Robocorp Code Package Activated Interpreter (Python Environment)",
                    shellPath: "C:\\Windows\\System32\\cmd.exe",
                });
                const varsFilePath = pathModule.join(env.RCC_HOLOTREE_SPACE_ROOT, "environment_vars.bat");
                const envVarsContent = Object.keys(env)
                    .reduce((acc, key) => {
                        return `${acc}SET ${key}=${env[key]}\n`;
                    }, "")
                    .trim();
                OUTPUT_CHANNEL.appendLine("Create terminal with RCC: " + envVarsContent);
                fsModule.writeFileSync(varsFilePath, envVarsContent);
                terminal.sendText(`call ${varsFilePath}\n`);
                terminal.show();
            } else {
                // The shell in UNIX doesn't matter that much as the syntax to set the Python Environment is common
                const terminal = window.createTerminal({
                    name: robotInfo.name + " Package environment",
                    env: env,
                    cwd: pathModule.dirname(robotInfo.filePath),
                    message: "Robocorp Code Package Activated Interpreter (Python Environment)",
                });
                const varsFilePath = pathModule.join(env.RCC_HOLOTREE_SPACE_ROOT, "environment_vars.sh");
                const envVarsContent = Object.keys(env)
                    .reduce((acc, key) => {
                        return `${acc}export ${key}=${env[key]}\n`;
                    }, "")
                    .trim();
                OUTPUT_CHANNEL.appendLine("Create terminal with RCC: " + envVarsContent);
                fsModule.writeFileSync(varsFilePath, envVarsContent);
                terminal.sendText(`source ${varsFilePath}\n`);
                terminal.show();
            }

            OUTPUT_CHANNEL.appendLine("Terminal created!");
            return undefined;
        }

        await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: "Start RCC shell for: " + robotInfo.name,
                cancellable: false,
            },
            startShell
        );
    }
}
