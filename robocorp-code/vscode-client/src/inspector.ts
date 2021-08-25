import * as path from 'path';
import {commands, Progress, ProgressLocation, window} from 'vscode'
import {ROBOCORP_GET_LANGUAGE_SERVER_PYTHON_INFO} from './robocorpCommands';
import {getRccLocation} from './rcc'
import {getExtensionRelativeFile, verifyFileExists} from './files'
import {listAndAskRobotSelection} from './activities'
import {getSelectedLocator, getSelectedRobot, LocatorEntry} from './viewsCommon';
import {sleep, Timing} from './time'
import {execFilePromise, ExecFileReturn} from './subprocess'
import * as roboConfig from './robocorpSettings';
import {OUTPUT_CHANNEL} from './channel';

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

let _cachedInspectorPythonInfo: InterpreterInfo;

export async function openRobocorpInspector(locatorType?: string, locator?: LocatorEntry): Promise<void> {
    let locatorJson;
    const args: string[] = [];
    let robot: LocalRobotMetadataInfo | undefined = getSelectedRobot('Please select a robot first.')?.robot;
    if (!robot) {
        // Ask for the robot to be used and then show dialog with the options.
        robot = await listAndAskRobotSelection(
          'Please select the Robot where the locators should be saved.',
          'Unable to create locator (no Robot detected in the Workspace).'
        );
        if (!robot) return;
    }
    const robotYaml = robot.filePath;
    locatorJson = path.join(robot.directory, "locators.json")
    locatorJson = verifyFileExists(locatorJson) ? locatorJson : undefined;
    let inspectorLaunchInfo = await commands.executeCommand(ROBOCORP_GET_LANGUAGE_SERVER_PYTHON_INFO) as InterpreterInfo | undefined;
    if (!inspectorLaunchInfo) {
            OUTPUT_CHANNEL.appendLine("Unable to get Robocorp Inspector launch info.");
            return;
        }

    // add locators.json path to args
    if(locatorJson) args.push("--database", locatorJson);

    // if locatorType is given prioritize that. Else Ensure that a locator is selected!
    if (locatorType) {
        args.push("add");
        args.push(locatorType)
    } else {
        const locatorSelected: LocatorEntry | undefined = locator ?? getSelectedLocator(
          "Please select a locator first.",
          "Please select only one locator.",
        );
        if (locatorSelected.type === "error") {
            OUTPUT_CHANNEL.appendLine("Trying to edit non-existing locator.");
            return;
        }
        if (locatorSelected) args.push("edit", locatorSelected.name)
        else {
            OUTPUT_CHANNEL.appendLine("Unable to open Robocorp Inspector. Select a locator first.");
            return;
        }
    }
    window.withProgress({
          location: ProgressLocation.Notification,
          title: "Robocorp",
          cancellable: false,
      },
      (progress) => {
        progress.report({ message: 'Opening Inspector...' });
        return new Promise<void>(resolve => {
              setTimeout(() => {
                  resolve();
              }, 3000);
          })
      });
    OUTPUT_CHANNEL.appendLine(`Args for inspector: ${args.join(", ")}`);
    const launchResult: ExecFileReturn = await startInspectorCLI(
      inspectorLaunchInfo.pythonExe,
      args,
      inspectorLaunchInfo.environ);
    OUTPUT_CHANNEL.appendLine('Inspector CLI stdout:');
    OUTPUT_CHANNEL.appendLine(launchResult.stdout);
    OUTPUT_CHANNEL.appendLine('Inspector CLI stderr:');
    OUTPUT_CHANNEL.appendLine(launchResult.stderr);
}



export async function getInspectorPythonInfo(): Promise<InterpreterInfo | undefined> {
    if (_cachedInspectorPythonInfo) {
        OUTPUT_CHANNEL.appendLine('Using CACHED getInspectorPythonInfo');
        return _cachedInspectorPythonInfo;
    }
    OUTPUT_CHANNEL.appendLine('Fetch getInspectorPythonInfo');
    let cachedInspectorPythonInfo = await getInspectorPythonInfoUncached();
    if (!cachedInspectorPythonInfo) {
        return undefined; // Unable to get it.
    }
    // Ok, we got it (cache that info).
    _cachedInspectorPythonInfo = cachedInspectorPythonInfo;
    return _cachedInspectorPythonInfo;
}


async function startInspectorCLI(pythonExecutable: string, args: string[], environ?: { [key: string]: string }): Promise<ExecFileReturn> {
    const inspectorCmd = ['-m', 'inspector.cli'];
    const completeArgs = inspectorCmd.concat(args)
    return execFilePromise(
      pythonExecutable, completeArgs,
      {env: {...process.env, ...environ}}
    );
}

const getInspectorPythonInfoUncached = async (): Promise<InterpreterInfo | undefined> => {
    let rccLocation = await getRccLocation();
    if (!rccLocation) {
        return;
    }
    let robotYaml = getExtensionRelativeFile('../../bin/create_inspector_env/robot.yaml');
    if (!robotYaml) {
        return;
    }

    async function createInspectorEnv(progress: Progress<{ message?: string; increment?: number }>): Promise<ExecFileReturn> | undefined {
        progress.report({ message: 'Setting up Robocorp Inspector env (may take a few minutes).' });
        // Get information on a base package with our basic dependencies (this can take a while...).
        let resultPromise: Promise<ExecFileReturn> = execFilePromise(
            rccLocation, ['task', 'run', '--robot', robotYaml, '--controller', 'RobocorpCode'],
            { env: { ...process.env, ROBOCORP_HOME: roboConfig.getHome() } }
        );
        let timing = new Timing();

        let finishedCondaRun = false;
        let onFinish = function () {
            finishedCondaRun = true;
        }
        resultPromise.then(onFinish, onFinish);

        // Busy async loop so that we can show the elapsed time.
        while (true) {
            await sleep(93); // Strange sleep so it's not always a .0 when showing ;)
            if (finishedCondaRun) {
                break;
            }
            if (timing.elapsedFromLastMeasurement(5000)) {
                progress.report({ message: 'Preparing Robocorp Inspector (may take a few minutes). ' + timing.getTotalElapsedAsStr() + ' elapsed.' });
            }
        }
        let result = await resultPromise;
        OUTPUT_CHANNEL.appendLine('Took ' + timing.getTotalElapsedAsStr() + ' to update prepare Robocorp Inspector.')
        return result;
    }

    let result: ExecFileReturn | undefined = await window.withProgress({
        location: ProgressLocation.Notification,
        title: "Robocorp",
        cancellable: false
    }, createInspectorEnv);

    function disabled(msg: string): undefined {
        msg = 'Robocorp Code extension disabled. Reason: ' + msg;
        OUTPUT_CHANNEL.appendLine(msg);
        window.showErrorMessage(msg);
        return undefined;
    }

    if (!result) {
        return disabled('Unable to get python to launch language server.');
    }

    try {
        let jsonContents = result.stderr;
        let start: number = jsonContents.indexOf('JSON START>>')
        let end: number = jsonContents.indexOf('<<JSON END')
        if (start == -1 || end == -1) {
            throw Error("Unable to find JSON START>> or <<JSON END");
        }
        start += 'JSON START>>'.length;
        jsonContents = jsonContents.substr(start, end - start);
        OUTPUT_CHANNEL.appendLine('Parsing json contents: ' + jsonContents);
        let contents: object = JSON.parse(jsonContents);
        let pythonExe = contents['python_executable'];
        if (verifyFileExists(pythonExe)) {
            return {
                pythonExe: pythonExe,
                environ: contents['environment'],
                additionalPythonpathEntries: [],
            };
        }
        return disabled('Python executable: ' + pythonExe + ' does not exist.');
    } catch (error) {
        return disabled('Unable to get python to launch language server.\nStderr: ' + result.stderr + '\nStdout (json contents): ' + result.stdout);
    }
}

