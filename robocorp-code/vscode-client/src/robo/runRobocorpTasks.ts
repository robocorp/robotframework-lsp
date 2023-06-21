import { DebugConfiguration, DebugSessionOptions, debug } from "vscode";

export async function runRobocorpTasks(noDebug: boolean, args: string[]) {
    let debugConfiguration: DebugConfiguration = {
        "name": "Python: Robocorp Tasks",
        "type": "python",
        "request": "launch",
        "module": "robocorp.tasks",
        "args": ["run"].concat(args),
        "justMyCode": true,
        "noDebug": noDebug,
    };

    let debugSessionOptions: DebugSessionOptions = {};
    debug.startDebugging(undefined, debugConfiguration, debugSessionOptions);
}
