import { Progress, ProgressLocation, window } from "vscode";
import { OUTPUT_CHANNEL } from "./channel";
import { getRccLocation } from "./rcc";
import * as roboConfig from './robocorpSettings';
import * as pathModule from 'path';
import { execFilePromise, ExecFileReturn } from "./subprocess";
import { listAndAskRobotSelection } from "./activities";

export async function askAndCreateRccTerminal() {
    let robot: LocalRobotMetadataInfo = await listAndAskRobotSelection(
        'Please select the target Robot for the terminal.',
        'Unable to create terminal (no Robot detected in the Workspace).'
    );
    if(robot){
        await createRccTerminal(robot);
    }
}

export async function createRccTerminal(robotInfo: LocalRobotMetadataInfo) {
    const rccLocation = await getRccLocation();
    if (!rccLocation) {
        window.showErrorMessage('Unable to find RCC to create terminal.');
        return;
    }

    let robocorpHome: string = roboConfig.getHome();
    let env = { ...process.env }
    if (robocorpHome) {
        env['ROBOCORP_HOME'] = robocorpHome;
    }

    if (robotInfo) {

        async function startShell(progress: Progress<{ message?: string; increment?: number }>): Promise<undefined> {
            let execFileReturn: ExecFileReturn = await execFilePromise(
                rccLocation, ['env', 'variables', '-j', '-r', robotInfo.filePath, '--controller', 'RobocorpCode'],
                { env: env }
            );
            if (execFileReturn.stdout) {
                let envArray = JSON.parse(execFileReturn.stdout);
                for (let index = 0; index < envArray.length; index++) {
                    const element = envArray[index];
                    let key: string = element['key'];
                    let isPath: boolean = false;
                    if (process.platform == 'win32') {
                        if (key.toLowerCase() == 'path') {
                            isPath = true;
                        }
                    } else {
                        if (key == 'PATH') {
                            isPath = true;
                        }
                    }
                    if (isPath) {
                        env[key] = pathModule.dirname(rccLocation) + pathModule.delimiter + element['value'];
                    } else {
                        env[key] = element['value'];
                    }
                }
                if(robocorpHome){
                    env['ROBOCORP_HOME'] = robocorpHome;
                }

                OUTPUT_CHANNEL.appendLine('Create terminal with RCC:' + rccLocation + ' for Robot: ' + robotInfo.name);
                const terminal = window.createTerminal({
                    name: robotInfo.name + ' Robot environment',
                    env: env,
                    cwd: pathModule.dirname(robotInfo.filePath),
                });

                terminal.show();
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