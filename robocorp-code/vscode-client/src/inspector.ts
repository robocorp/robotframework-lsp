import * as path from "path";
import { ProgressLocation, window } from "vscode";
import { getLanguageServerPythonInfo } from "./extension";
import { verifyFileExists } from "./files";
import { listAndAskRobotSelection } from "./activities";
import { getSelectedLocator, getSelectedRobot, LocatorEntry } from "./viewsCommon";
import { execFilePromise, ExecFileReturn } from "./subprocess";
import { OUTPUT_CHANNEL } from "./channel";

export async function openRobocorpInspector(locatorType?: string, locator?: LocatorEntry): Promise<void> {
    let locatorJson;
    const args: string[] = [];
    let robot: LocalRobotMetadataInfo | undefined = getSelectedRobot("Please select a robot first.")?.robot;
    if (!robot) {
        // Ask for the robot to be used and then show dialog with the options.
        robot = await listAndAskRobotSelection(
            "Please select the Robot where the locators should be saved.",
            "Unable to create locator (no Robot detected in the Workspace)."
        );
        if (!robot) return;
    }
    locatorJson = path.join(robot.directory, "locators.json");
    locatorJson = verifyFileExists(locatorJson, false) ? locatorJson : undefined;
    const inspectorLaunchInfo = await getLanguageServerPythonInfo();
    if (!inspectorLaunchInfo) {
        OUTPUT_CHANNEL.appendLine("Unable to get Robocorp Inspector launch info.");
        return;
    }

    // add locators.json path to args
    if (locatorJson) args.push("--database", locatorJson);

    // if locatorType is given prioritize that. Else Ensure that a locator is selected!
    if (locatorType) {
        args.push("add");
        args.push(locatorType);
    } else {
        const locatorSelected: LocatorEntry | undefined =
            locator ?? getSelectedLocator("Please select a locator first.", "Please select only one locator.");
        if (locatorSelected.type === "error") {
            OUTPUT_CHANNEL.appendLine("Trying to edit non-existing locator.");
            return;
        }
        if (locatorSelected) args.push("edit", locatorSelected.name);
        else {
            OUTPUT_CHANNEL.appendLine("Unable to open Robocorp Inspector. Select a locator first.");
            return;
        }
    }
    window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Robocorp",
            cancellable: false,
        },
        (progress) => {
            progress.report({ message: "Opening Inspector..." });
            return new Promise<void>((resolve) => {
                setTimeout(() => {
                    resolve();
                }, 3000);
            });
        }
    );

    // Required due to how conda packages python, and MacOS requiring
    // a signed package for displaying windows (supplied through python.app)
    const pythonExecutablePath =
        process.platform === "darwin"
            ? path.join(path.dirname(inspectorLaunchInfo.pythonExe), "pythonw")
            : inspectorLaunchInfo.pythonExe;
    const launchResult: ExecFileReturn = await startInspectorCLI(
        pythonExecutablePath,
        args,
        robot.directory,
        inspectorLaunchInfo.environ
    );
    OUTPUT_CHANNEL.appendLine("Inspector CLI stdout:");
    OUTPUT_CHANNEL.appendLine(launchResult.stdout);
    OUTPUT_CHANNEL.appendLine("Inspector CLI stderr:");
    OUTPUT_CHANNEL.appendLine(launchResult.stderr);
}

async function startInspectorCLI(
    pythonExecutable: string,
    args: string[],
    cwd?: string,
    environ?: { [key: string]: string }
): Promise<ExecFileReturn> {
    const inspectorCmd = ["-m", "inspector.cli"];
    const completeArgs = inspectorCmd.concat(args);
    OUTPUT_CHANNEL.appendLine(`Using cwd root for inspector: "${cwd}"`);
    return execFilePromise(pythonExecutable, completeArgs, {
        env: { ...process.env, ...environ },
        cwd,
    });
}
