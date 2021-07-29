import { workspace, WorkspaceConfiguration } from "vscode";
import { OUTPUT_CHANNEL } from "./extension";

interface IGetVar {
    (name: string): string;
}

/**
 * It'd be nicer is VSCode itself provided such an API, but alas, it's not really
 * available, so, we need to reimplement it...
 */
export function expandVars(template: string) {
    let getVar: IGetVar = function getVar(name: string) {
        if (name == "${workspace}" || name == "${workspaceRoot}" || name == "${workspaceFolder}") {
            let workspaceFolders = workspace.workspaceFolders;
            if (workspaceFolders && workspaceFolders.length > 0) {
                return workspaceFolders[0].uri.fsPath;
            }
        } else if ((name.startsWith("${env.") || name.startsWith("${env:")) && name.endsWith("}")) {
            let varName = name.substring(6, name.length - 1);
            let value = process.env[varName];
            if (value) {
                return value;
            }
        }
        OUTPUT_CHANNEL.appendLine('Unable to resolve variable: ' + name);
        return name;
    }
    let ret = template.replace(/\${([^{}]*)}/g, getVar);
    if (ret.startsWith("~")) {
        const homedir = require('os').homedir();
        return homedir + ret.substr(1);
    }
    return ret;
}

export function getStrFromConfigExpandingVars(config: WorkspaceConfiguration, name: string): string | undefined {
    let value: string = config.get<string>(name);
    if (typeof value !== "string") {
        OUTPUT_CHANNEL.appendLine('Expected string for configuration: ' + name);
        return undefined;
    }
    return expandVars(value);
}

export function getArrayStrFromConfigExpandingVars(config: WorkspaceConfiguration, name: string): Array<string> | undefined {
    let array: Array<string> = config.get<Array<string>>(name);
    if (array) {
        if (!Array.isArray(array)) {
            OUTPUT_CHANNEL.appendLine('Expected string[] for configuration: ' + name);
            return undefined;
        }
        let ret: Array<string> = [];
        for (const s of array) {
            if (typeof s !== "string") {
                ret.push(expandVars("" + s));
            } else {
                ret.push(expandVars(s));
            }
        }
        return ret;
    }
    return array;
}