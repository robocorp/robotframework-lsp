import { Progress, ProgressLocation, window } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import * as pathModule from 'path';
import { listAndAskRobotSelection } from "./activities";
import * as roboConfig from './robocorpSettings';
import { collectEnv } from "./rcc";

export async function askAndCreateRccTerminal() {
    let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
        'Please select the target Robot for the terminal.',
        'Unable to create terminal (no Robot detected in the Workspace).'
    );
    if (robot) {
        await createRccTerminal(robot);
    }
}

export async function createRccTerminal(robotInfo: LocalRobotMetadataInfo) {
    if (robotInfo) {
        async function startShell(progress: Progress<{ message?: string; increment?: number }>): Promise<undefined> {
            let rccEnv = await collectEnv(robotInfo.filePath, 'vscode-terminal-', roboConfig.getHome(), true);
            if (rccEnv !== undefined) {
                OUTPUT_CHANNEL.appendLine('Create terminal with RCC:' + rccEnv.rccLocation + ' for Robot: ' + robotInfo.name);
                const terminal = window.createTerminal({
                    name: robotInfo.name + ' Robot environment',
                    env: rccEnv.env,
                    cwd: pathModule.dirname(robotInfo.filePath),
                });

                terminal.show();
            } else {
                OUTPUT_CHANNEL.appendLine('Unable to collect environment to create terminal with RCC:' + rccEnv.rccLocation + ' for Robot: ' + robotInfo.name);
            }
            return undefined;
        }

        await window.withProgress({
            location: ProgressLocation.Notification,
            title: 'Robocorp: start RCC shell for: ' + robotInfo.name + ' Robot',
            cancellable: false
        }, startShell);

    }
}