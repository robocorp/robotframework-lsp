import path = require("path");
import * as vscode from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { readLaunchTemplate } from "./run";
import { WeakValueMap } from "./weakValueMap";
import { jsonEscapeUTF } from "./escape";

import * as nodePath from "path";
import { sleep } from "./time";
import { getWorkspaceFolderForUriAndShowInfoIfNotFound } from "./common";

const posixPath = nodePath.posix || nodePath;

export interface IPosition {
    // Line position in a document (zero-based).
    line: number;

    // Character offset on a line in a document (zero-based). Assuming that
    // the line is represented as a string, the `character` value represents
    // the gap between the `character` and `character + 1`.
    //
    // If the character value is greater than the line length it defaults back
    // to the line length.
    character: number;
}

export interface IRange {
    start: IPosition;
    end: IPosition;
}

export interface ITestInfoFromSymbolsCache {
    name: string;
    range: IRange;
}

export interface ITestInfoFromUri {
    uri: string;
    testInfo: ITestInfoFromSymbolsCache[];
}

const controller = vscode.workspace.getConfiguration("robot.testView").get<boolean>("enabled")
    ? vscode.tests.createTestController("robotframework-lsp.testController", "Robot Framework")
    : undefined;

const runProfile = controller?.createRunProfile("Run", vscode.TestRunProfileKind.Run, (request, token) => {
    runHandler(false, request, token);
});

const debugProfile = controller?.createRunProfile("Debug", vscode.TestRunProfileKind.Debug, (request, token) => {
    runHandler(true, request, token);
});

export const TEST_CONTROLLER = controller;
export const RUN_PROFILE = runProfile;
export const DEBUG_PROFILE = debugProfile;

// Note: we cannot assign the resolveHandler (if we do that
// VSCode will clear the existing items, which is not what
// we want -- with our current approach we start collecting
// when the extension is started).
// controller.resolveHandler = async (test) => {
//     if (!test) {
//         // Wait for the first full refresh.
//         controller.items.replace([]);
//         testItemIdToTestItem.clear();
//         await vscode.commands.executeCommand("robot.waitFullTestCollection.internal");
//     }
// };

export async function clearTestItems() {
    if (!controller) return;
    controller.items.replace([]);
    testItemIdToTestItem.clear();
}

enum ItemType {
    File,
    TestCase,
}

interface ITestData {
    type: ItemType;
    testInfo: ITestInfoFromSymbolsCache | undefined;
}

const testData = new WeakMap<vscode.TestItem, ITestData>(); // Actually weak key map.

let lastRunId = 0;
export function nextRunId(): string {
    lastRunId += 1;
    return `Run: ${lastRunId}`;
}

const runIdToTestRun = new Map<string, vscode.TestRun>();
const runIdToDebugSession = new Map<string, vscode.DebugSession>();

// Note: a test item id is uri a string such as:
// `${uri} [${testName}]`
const testItemIdToTestItem = new WeakValueMap<string, vscode.TestItem>();

export function computeUriTestId(uri: string): string {
    if (uri.startsWith("id:")) {
        throw new Error("It seems that this uri is actually a test id already.");
    }
    if (process.platform == "win32") {
        uri = uri.toLowerCase();
    }
    return "id:" + uri;
}

export function computeTestIdFromTestInfo(uriAsStr: string, test: ITestInfoFromSymbolsCache): string {
    uriAsStr = computeUriTestId(uriAsStr);
    return `${uriAsStr} [${test.name}]`;
}

export function computeTestId(uri: string, name: string): string {
    uri = computeUriTestId(uri);
    return `${uri} [${name}]`;
}

function getType(testItem: vscode.TestItem): ItemType {
    const data = testData.get(testItem);
    if (!data) {
        return undefined;
    }
    return data.type;
}

function removeTreeStructure(uri: vscode.Uri) {
    while (true) {
        const uriAsStr = computeUriTestId(uri.toString());
        let testItem = getTestItem(uriAsStr);
        if (!testItem) {
            return;
        }
        testItemIdToTestItem.delete(uriAsStr);

        let parentItem = testItem.parent;
        if (parentItem) {
            if (parentItem.children.get(uriAsStr) !== undefined) {
                parentItem.children.delete(uriAsStr);
                if (parentItem.children.size == 0) {
                    uri = parentItem.uri;
                } else {
                    return;
                }
            } else {
                return;
            }
        } else {
            let file = controller.items.get(uriAsStr);
            if (file !== undefined) {
                controller.items.delete(uriAsStr);
            }
            return;
        }
    }
}

function addTreeStructure(workspaceFolder: vscode.WorkspaceFolder, uri: vscode.Uri): vscode.TestItem {
    let workspaceFolderPath = workspaceFolder.uri.path;
    let uriPath = uri.path;
    if (process.platform == "win32") {
        workspaceFolderPath = workspaceFolderPath.toLowerCase();
        uriPath = uriPath.toLowerCase();
    }
    const path = posixPath.relative(workspaceFolderPath, uriPath);
    const parts = path.split("/");

    let prev = workspaceFolder.uri.path;
    let parentItem: vscode.TestItem | undefined = undefined;
    let ret: vscode.TestItem | undefined = undefined;

    for (const part of parts) {
        const next = `${prev}/${part}`;
        const nextUri = uri.with({ "path": next });
        const nextUriStr = computeUriTestId(nextUri.toString());

        ret = getTestItem(nextUriStr);
        if (!ret) {
            // Just create if it still wasn't created (otherwise we'd override
            // the previously created item/children structure).
            ret = controller.createTestItem(nextUriStr, part, nextUri);
            testItemIdToTestItem.set(nextUriStr, ret);
            testData.set(ret, { type: ItemType.File, testInfo: undefined });
            if (parentItem === undefined) {
                controller.items.add(ret);
            } else {
                parentItem.children.add(ret);
            }
        }

        parentItem = ret;
        prev = next;
    }

    return ret;
}

export async function handleTestsCollected(testInfo: ITestInfoFromUri) {
    const uri = vscode.Uri.parse(testInfo.uri);

    const workspaceFolder = getWorkspaceFolderForUriAndShowInfoIfNotFound(uri);
    if (workspaceFolder === undefined) {
        return;
    }

    if (testInfo.testInfo.length === 0) {
        removeTreeStructure(uri);
        return;
    }

    const file = addTreeStructure(workspaceFolder, uri);

    const uriAsStr = uri.toString();
    const children: vscode.TestItem[] = [];
    const found: Set<string> = new Set();

    for (const test of testInfo.testInfo) {
        const testItemId = computeTestIdFromTestInfo(uriAsStr, test);
        if (found.has(testItemId)) {
            continue;
        }
        found.add(testItemId);
        const testItem: vscode.TestItem = controller.createTestItem(testItemId, test.name, uri);
        testItemIdToTestItem.set(testItemId, testItem);
        const start = new vscode.Position(test.range.start.line, test.range.start.character);
        const end = new vscode.Position(test.range.end.line, test.range.end.character);
        testItem.range = new vscode.Range(start, end);
        testData.set(testItem, { type: ItemType.TestCase, testInfo: test });
        children.push(testItem);
    }

    if (vscode.version.startsWith("1.63.")) {
        // Intentionally make a flicker to workaround https://github.com/microsoft/vscode/issues/140166.
        // This is fixed in current insiders (1.64).
        file.children.replace([]);
        await sleep(400);
    }

    file.children.replace(children);
}

export function getTestItem(testId: string): vscode.TestItem {
    if (!testId.startsWith("id:")) {
        throw new Error("Expected testId to start with 'id:'. Found: " + testId);
    }
    return testItemIdToTestItem.get(testId);
}

async function runHandler(shouldDebug: boolean, request: vscode.TestRunRequest, token: vscode.CancellationToken) {
    const queue: vscode.TestItem[] = [];

    if (request.include) {
        request.include.forEach((test) => queue.push(test));
    } else {
        controller.items.forEach((test) => queue.push(test));
    }

    let includeTests: vscode.TestItem[] = [];
    let excludeTests: vscode.TestItem[] = [];
    let workspaceFolders = new Set<vscode.WorkspaceFolder>();

    while (queue.length > 0 && !token.isCancellationRequested) {
        const test = queue.pop()!;
        let uri = test.uri;
        let workspaceFolder = getWorkspaceFolderForUriAndShowInfoIfNotFound(uri);
        if (workspaceFolder) {
            workspaceFolders.add(workspaceFolder);
        } else {
            OUTPUT_CHANNEL.appendLine("Could not find workspace folder for uri: " + uri);
        }
        includeTests.push(test);
    }

    if (request.exclude) {
        for (const test of request.exclude) {
            excludeTests.push(test);
        }
    }

    if (token.isCancellationRequested) {
        return;
    }

    if (workspaceFolders.size > 1) {
        OUTPUT_CHANNEL.appendLine(
            "Note: tests span more than 1 workspace folder. Launch templates will only take the first one into account."
        );
    } else if (workspaceFolders.size == 0) {
        vscode.window.showErrorMessage("Unable to launch because workspace folder is not available.");
        return;
    }
    let wsFoldersAsArray: vscode.WorkspaceFolder[] = [];
    for (const ws of workspaceFolders) {
        wsFoldersAsArray.push(ws);
    }

    // Note: make sure to end the run after all tests have been executed.
    const run = controller.createTestRun(request);
    const runId: string = obtainRunId(run);

    await launch(wsFoldersAsArray, runId, includeTests, excludeTests, shouldDebug);
}

function obtainRunId(run: vscode.TestRun): string {
    const runId = nextRunId();
    runIdToTestRun.set(runId, run);
    return runId;
}

function handleTestRunFinished(runId: string) {
    if (runIdToDebugSession.has(runId)) {
        runIdToDebugSession.delete(runId);
    }
    if (runIdToTestRun.has(runId)) {
        const testRun = runIdToTestRun.get(runId);
        runIdToTestRun.delete(runId);
        testRun.end();
    }
}

async function launch(
    workspaceFolders: vscode.WorkspaceFolder[],
    runId: string,
    includeTests: vscode.TestItem[], // the tests to be included
    excludeTests: vscode.TestItem[], // the tests to be excluded
    shouldDebug: boolean
): Promise<boolean> {
    let cwd: string;
    let launchTemplate: vscode.DebugConfiguration = undefined;
    cwd = workspaceFolders[0].uri.fsPath;
    launchTemplate = await readLaunchTemplate(workspaceFolders[0]);

    let args: string[] = [];

    // We want the events both in run and debug in this case.
    args.push("--listener=robotframework_debug_adapter.events_listener.EventsListenerV2");
    args.push("--listener=robotframework_debug_adapter.events_listener.EventsListenerV3");

    // Include/exclude tests based on RFLS_PRERUN_FILTERING env variable.
    let envFiltering: string | undefined = undefined;
    function convertToFiltering(collection: vscode.TestItem[]) {
        let ret = [];
        for (const test of collection) {
            if (getType(test) === ItemType.TestCase) {
                let data = testData.get(test);
                if (!data) {
                    OUTPUT_CHANNEL.appendLine("Unable to find test data for: " + test.id);
                    continue;
                }
                ret.push([test.uri.fsPath, data.testInfo.name]);
            } else {
                ret.push([test.uri.fsPath, "*"]);
            }
        }
        return ret;
    }

    envFiltering = jsonEscapeUTF(
        JSON.stringify({
            "include": convertToFiltering(includeTests),
            "exclude": convertToFiltering(excludeTests),
        })
    );

    let debugConfiguration: vscode.DebugConfiguration = {
        "type": "robotframework-lsp",
        "runId": runId,
        "name": "Robot Framework: Launch " + runId,
        "request": "launch",
        "cwd": cwd,
        "terminal": "integrated",
        "env": {},
        "args": args,
    };

    if (launchTemplate) {
        for (var key of Object.keys(launchTemplate)) {
            if (key !== "type" && key !== "name" && key !== "request") {
                let value = launchTemplate[key];
                if (value !== undefined) {
                    if (key === "args") {
                        try {
                            debugConfiguration.args = debugConfiguration.args.concat(value);
                        } catch (err) {
                            logError(
                                "Unable to concatenate: " + debugConfiguration.args + " to: " + value,
                                err,
                                "RUN_CONCAT_ARGS"
                            );
                        }
                    } else {
                        debugConfiguration[key] = value;
                    }
                }
            }
        }
    }

    if (debugConfiguration.makeSuite === undefined) {
        // Not in template (default == true)
        debugConfiguration.makeSuite = true;
    }

    // Note that target is unused if RFLS_PRERUN_FILTER_TESTS is specified and makeSuite == true.
    let targetAsSet = new Set<string>();
    for (const test of includeTests) {
        targetAsSet.add(test.uri.fsPath);
    }
    let target: string[] = [];
    for (const s of targetAsSet) {
        target.push(s);
    }
    debugConfiguration.target = target;

    if (debugConfiguration.makeSuite) {
        if (workspaceFolders.length > 1) {
            let suiteTarget = [];
            for (const ws of workspaceFolders) {
                suiteTarget.push(ws.uri.fsPath);
            }
            debugConfiguration["suiteTarget"] = suiteTarget;
        }
    }

    if (!debugConfiguration.env) {
        debugConfiguration.env = { "RFLS_PRERUN_FILTER_TESTS": envFiltering };
    } else {
        debugConfiguration.env["RFLS_PRERUN_FILTER_TESTS"] = envFiltering;
    }

    let debugSessionOptions: vscode.DebugSessionOptions = { "noDebug": !shouldDebug };
    const started: boolean = await launchDebugSession(
        runId,
        workspaceFolders[0],
        debugConfiguration,
        debugSessionOptions
    );
    return started;
}

async function launchDebugSession(
    runId: string,
    workspaceFolder: vscode.WorkspaceFolder,
    debugConfiguration: vscode.DebugConfiguration,
    debugSessionOptions: vscode.DebugSessionOptions
) {
    debugConfiguration.runId = runId;
    let started = await vscode.debug.startDebugging(workspaceFolder, debugConfiguration, debugSessionOptions);
    if (!started) {
        handleTestRunFinished(runId);
    }
    return started;
}

export async function setupTestExplorerSupport() {
    function isRelatedSession(session: vscode.DebugSession) {
        return session.configuration.type === "robotframework-lsp" && session.configuration.runId !== undefined;
    }

    vscode.debug.onDidStartDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            OUTPUT_CHANNEL.appendLine("Started testview debug session " + session.configuration.runId);
            if (runIdToTestRun.has(session.configuration.runId)) {
                runIdToDebugSession.set(session.configuration.runId, session);
            }
        }
    });

    vscode.debug.onDidTerminateDebugSession((session: vscode.DebugSession) => {
        if (isRelatedSession(session)) {
            handleTestRunFinished(session.configuration.runId);
        }
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent((event: vscode.DebugSessionCustomEvent) => {
        // OUTPUT_CHANNEL.appendLine("Received event: " + event.event + " -- " + JSON.stringify(event.body));
        try {
            if (isRelatedSession(event.session)) {
                const runId = event.session.configuration.runId;
                const testRun = runIdToTestRun.get(runId);
                if (testRun) {
                    switch (event.event) {
                        case "startSuite":
                            handleSuiteStart(testRun, event);
                            break;
                        case "endSuite":
                            handleSuiteEnd(testRun, event);
                            break;
                        case "startTest":
                            handleTestStart(testRun, event);
                            break;
                        case "endTest":
                            handleTestEnd(testRun, event);
                            break;
                        case "logMessage":
                            handleLogMessage(testRun, event);
                            break;
                    }
                }
            }
        } catch (err) {
            logError("Error handling debug session event: " + JSON.stringify(event), err, "HANDLE_DEBUG_SESSION_EVENT");
        }
    });
}

// Constants to color (we could move this somewhere in the future if
// we need to use it elsewhere).
const red = "\u001b[31m";
const green = "\u001b[32m";
const yellow = "\u001b[33m";
const blue = "\u001b[34m";
const magenta = "\u001b[35m";
const cyan = "\u001b[36m";
const white = "\u001b[37m";
const reset = "\u001b[0m";

function handleLogMessage(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    let message = event.body.message;
    let level = event.body.level;

    let testItem = undefined;
    let location = undefined;

    // If we report this here, VSCode may not show the error messages properly, so, leave it out for now.
    if (event.body.testOrSuiteSource) {
        let testName: string | undefined = event.body.testName;
        let uri = vscode.Uri.file(event.body.testOrSuiteSource);
        const uriStr = uri.toString();
        let testId: string;
        if (testName) {
            testId = computeTestId(uriStr, testName);
        } else {
            testId = computeUriTestId(uriStr);
        }
        testItem = getTestItem(testId);
    }

    if (testItem && event.body.source && !event.body.source.startsWith("<")) {
        let lineno: number | undefined = event.body.lineno || 0;
        if (lineno) {
            lineno = lineno - 1;
        }
        let uri = vscode.Uri.file(event.body.source);
        const uriStr = uri.toString();

        if (lineno !== undefined && testItem !== undefined) {
            let range = new vscode.Position(lineno, 0);
            location = new vscode.Location(uri, range);
        }
    }

    try {
        message = message.split(/(?:\r\n|\r|\n)/g).join("\r\n");
    } catch (err) {
        logError(
            "Error handling log message: " + JSON.stringify(message) + " (" + typeof message + ")",
            err,
            "HANDLE_LOG_MESSAGE"
        );
    }

    message = `[LOG ${level}] ${message}`;

    const config = vscode.workspace.getConfiguration("robot.run.peekError");
    let configLevel: string = config.get<string>("level", "ERROR").toUpperCase().trim();
    if (configLevel != "INFO" && configLevel != "WARN" && configLevel != "ERROR" && configLevel != "NONE") {
        OUTPUT_CHANNEL.appendLine("Invalid robot.run.peekError.level: " + configLevel);
        configLevel = "ERROR";
    }

    let addToConsoleWithLocation: boolean;
    switch (level) {
        case "INFO":
            addToConsoleWithLocation = configLevel == "INFO";
            break;
        case "WARN":
            message = yellow + message + reset;
            addToConsoleWithLocation = configLevel == "INFO" || configLevel == "WARN";
            break;
        case "FAIL":
        case "ERROR":
            addToConsoleWithLocation = configLevel == "INFO" || configLevel == "WARN" || configLevel == "ERROR";
            message = red + message + reset;
            break;
    }

    if (addToConsoleWithLocation) {
        // When it's added to the console with the location it also appears
        // in the test result.
        testRun.appendOutput(message, location, testItem);
    } else {
        testRun.appendOutput(message);
    }
}

function handleSuiteStart(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const uriStr = vscode.Uri.file(event.body.source).toString();
    const testNames: string[] = event.body.tests;
    for (const testName of testNames) {
        const testId = computeTestId(uriStr, testName);
        const testItem = getTestItem(testId);
        if (!testItem) {
            OUTPUT_CHANNEL.appendLine("Did not find test item: " + testId);
            continue;
        } else {
            testRun.enqueued(testItem);
        }
    }
}

function handleTestStart(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const testUriStr = vscode.Uri.file(event.body.source).toString();
    const testName = event.body.name;
    const testId = computeTestId(testUriStr, testName);
    const testItem = getTestItem(testId);
    if (!testItem) {
        OUTPUT_CHANNEL.appendLine("Did not find test item: " + testId);
    } else {
        testRun.started(testItem);
    }
}

function buildTestMessages(event: vscode.DebugSessionCustomEvent): vscode.TestMessage[] {
    let messages: vscode.TestMessage[] = [];
    let msg = event.body.message;
    let config = vscode.workspace.getConfiguration("robot.run.peekError");
    if (msg) {
        if (config.get("showSummary", false)) {
            messages.push({
                "message": `[TEST] ${msg}`,
            });
        }
    }

    const failedKeywords = event.body.failed_keywords;
    if (failedKeywords) {
        if (config.get("showErrorsInCallers", false)) {
            for (const failed of failedKeywords) {
                messages.push({
                    "message": failed.message,
                    "location": {
                        "uri": vscode.Uri.file(failed.source),
                        "range": new vscode.Range(
                            new vscode.Position(failed.lineno - 1, 0),
                            new vscode.Position(failed.lineno - 1, 0)
                        ),
                    },
                });
            }
        }
    }
    return messages;
}

function handleSuiteEnd(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const uriStr = computeUriTestId(vscode.Uri.file(event.body.source).toString());
    const testItem = getTestItem(uriStr);
    markTestRun(testItem, uriStr, testRun, event);
}

function handleTestEnd(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const testUriStr = vscode.Uri.file(event.body.source).toString();
    const testName = event.body.name;
    const testId = computeTestId(testUriStr, testName);
    const testItem = getTestItem(testId);
    markTestRun(testItem, testId, testRun, event);
}

function markTestRun(
    testItem: vscode.TestItem,
    testId: string,
    testRun: vscode.TestRun,
    event: vscode.DebugSessionCustomEvent
) {
    if (!testItem) {
        OUTPUT_CHANNEL.appendLine("Did not find test item: " + testId);
    } else {
        switch (event.body.status) {
            case "SKIP":
                testRun.skipped(testItem);
                break;
            case "PASS":
                testRun.passed(testItem, event.body.elapsedtime);
                break;
            case "FAIL":
                testRun.failed(testItem, buildTestMessages(event), event.body.elapsedtime);
                break;
            default:
                testRun.errored(testItem, buildTestMessages(event), event.body.elapsedtime);
                break;
        }
    }
}
