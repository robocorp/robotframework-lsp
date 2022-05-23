import { commands, Progress, ProgressLocation, window } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import * as pathModule from "path";
import { listAndAskRobotSelection, resolveInterpreter } from "./activities";
import { getRccLocation } from "./rcc";
import { mergeEnviron } from "./subprocess";
import { getAutosetpythonextensiondisableactivateterminal } from "./robocorpSettings";
import { disablePythonTerminalActivateEnvironment } from "./pythonExtIntegration";

export async function askAndCreateRccTerminal() {
    let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
        "Please select the target Robot for the terminal.",
        "Unable to create terminal (no Robot detected in the Workspace)."
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
                let msg = "Unable to find RCC.";
                OUTPUT_CHANNEL.appendLine(
                    "Unable to collect environment to create terminal with RCC:" +
                        rccLocation +
                        " for Robot: " +
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

            OUTPUT_CHANNEL.appendLine("Create terminal with RCC:" + rccLocation + " for Robot: " + robotInfo.name);
            const terminal = window.createTerminal({
                name: robotInfo.name + " Robot environment",
                env: env,
                cwd: pathModule.dirname(robotInfo.filePath),
            });

            terminal.show();
            return undefined;
        }

        await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: "Robocorp: start RCC shell for: " + robotInfo.name + " Robot",
                cancellable: false,
            },
            startShell
        );
    }
}
