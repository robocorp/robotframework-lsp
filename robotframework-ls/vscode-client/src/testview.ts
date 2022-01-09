import path = require("path");
import * as vscode from "vscode";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { readLaunchTemplate } from "./run";
import { WeakValueMap } from "./weakValueMap";

import * as nodePath from "path";

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

const controller = vscode.tests.createTestController("robotframework-lsp.testController", "Robot Framework");

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
function nextRunId(): string {
    lastRunId += 1;
    return `TestRun: ${lastRunId}`;
}

const runIdToTestRun = new Map<string, vscode.TestRun>();
const runIdToDebugSession = new Map<string, vscode.DebugSession>();

// Note: a test item id is uri a string such as:
// `${uri} [${testName}]`
const testItemIdToTestItem = new WeakValueMap<string, vscode.TestItem>();

function computeTestIdFromTestInfo(uriAsStr: string, test: ITestInfoFromSymbolsCache): string {
    OUTPUT_CHANNEL.appendLine("Computed: " + `${uriAsStr} [${test.name}]`);
    return `${uriAsStr} [${test.name}]`;
}

function computeTestId(uri: string, name: string): string {
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
        const uriAsStr = uri.toString();
        let testItem = testItemIdToTestItem.get(uriAsStr);
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
    const path = posixPath.relative(workspaceFolder.uri.path, uri.path);
    const parts = path.split("/");

    let prev = workspaceFolder.uri.path;
    let parentItem: vscode.TestItem | undefined = undefined;
    let ret: vscode.TestItem | undefined = undefined;

    for (const part of parts) {
        const next = `${prev}/${part}`;
        const nextUri = uri.with({ "path": next });
        const nextUriStr = nextUri.toString();

        ret = testItemIdToTestItem.get(nextUriStr);
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

    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);

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
    file.children.replace(children);
}

export async function setupTestExplorerSupport() {
    async function runHandler(shouldDebug: boolean, request: vscode.TestRunRequest, token: vscode.CancellationToken) {
        const run = controller.createTestRun(request);
        const queue: vscode.TestItem[] = [];

        if (request.include) {
            request.include.forEach((test) => queue.push(test));
        } else {
            controller.items.forEach((test) => queue.push(test));
        }

        const testCases: vscode.TestItem[] = [];
        let includeTests: vscode.TestItem[] = [];
        let excludeTests: vscode.TestItem[] = [];

        let simpleMode = false;
        if (!request.exclude) {
            simpleMode = true;
            if (queue.length !== 1) {
                // When we have multiple items, we need to verify if simple mode is usable.
                let allTypesEqual = undefined;
                for (const test of queue) {
                    if (allTypesEqual === undefined) {
                        allTypesEqual = getType(test);
                    } else {
                        if (allTypesEqual !== getType(test)) {
                            allTypesEqual = undefined;
                            break;
                        }
                    }
                }

                if (allTypesEqual === ItemType.File) {
                    simpleMode = true;
                } else if (allTypesEqual === ItemType.TestCase) {
                    // Only simple if only one uri was used (for multiple files we
                    // need the non-simple mode).
                    let found = new Set();
                    for (const test of queue) {
                        found.add(test.uri);
                    }
                    simpleMode = found.size === 1;
                } else {
                    simpleMode = false;
                }
            }
        }

        if (simpleMode) {
            // Easy mode, just run everything included.
            while (queue.length > 0 && !token.isCancellationRequested) {
                const test = queue.pop()!;
                testCases.push(test);
            }
        } else {
            // In non-simple mode we fill test cases with the uris and
            // filter with the includes (excludes are applied here and
            // not in the backend).
            let includesAsSet: Set<vscode.TestItem> = new Set();
            while (queue.length > 0 && !token.isCancellationRequested) {
                const test = queue.pop()!;

                // Skip tests the user asked to exclude
                if (request.exclude?.includes(test)) {
                    continue;
                }

                switch (getType(test)) {
                    case ItemType.TestCase:
                        includesAsSet.add(test.parent); // deduplicate testCases
                        includeTests.push(test);
                        break;
                }

                test.children.forEach((test) => queue.push(test));
            }
            for (const test of includesAsSet) {
                testCases.push(test);
            }
        }

        if (token.isCancellationRequested) {
            return;
        }
        if (!testCases) {
            vscode.window.showInformationMessage("Nothing was run because all test cases were filtered out.");
            return;
        }
        let firstTestCase = testCases[0];
        let uri = firstTestCase.uri;

        let workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
        if (!workspaceFolder) {
            let folders = vscode.workspace.workspaceFolders;
            if (folders) {
                // Use the currently opened folder.
                workspaceFolder = folders[0];
            }
        }

        if (!workspaceFolder) {
            vscode.window.showErrorMessage("Unable to launch because workspace folder is not available.");
            return;
        }

        const runId = nextRunId();
        runIdToTestRun.set(runId, run);
        // Make sure to end the run after all tests have been executed:

        let launched = await launch(workspaceFolder, runId, testCases, includeTests, excludeTests, shouldDebug);
        if (!launched) {
            handleTestRunFinished(runId);
        }
        // For each test we need to call something as:
        // const start = Date.now();
        // run.started();
        // run.passed(test, Date.now() - start);
        // run.failed(test, new vscode.TestMessage(e.message), Date.now() - start);

        // When finished:
        // run.end();
    }

    async function launch(
        workspaceFolder: vscode.WorkspaceFolder,
        runId: string,
        // in general only this is needed (passes tests with args)
        // -- if filtering is needed this should include only the files.
        testCases: vscode.TestItem[],
        includeTests: vscode.TestItem[], // the tests to be included (if specific filtering by test names is needed)
        excludeTests: vscode.TestItem[], // the tests to be excluded (if specific filtering by test names is needed)
        shouldDebug: boolean
    ): Promise<boolean> {
        let cwd: string;
        let launchTemplate: vscode.DebugConfiguration = undefined;
        cwd = workspaceFolder.uri.fsPath;
        launchTemplate = await readLaunchTemplate(workspaceFolder);

        let args: string[] = [];
        let targets = new Set();

        // We want the events both in run and debug in this case.
        args.push("--listener=robotframework_debug_adapter.events_listener.EventsListenerV2");

        // Exclude tests based on RFLS_PRERUN_FILTERING env variable.
        let envFiltering: string | undefined = undefined;
        if (includeTests.length > 0 || excludeTests.length > 0) {
            args.push("--prerunmodifier=robotframework_debug_adapter.prerun_modifiers.FilteringTestsSuiteVisitor");

            function convertToFiltering(collection: vscode.TestItem[]) {
                let ret = [];
                for (const test of collection) {
                    let data = testData.get(test);
                    if (!data) {
                        OUTPUT_CHANNEL.appendLine("Unable to find test data for: " + test.id);
                        continue;
                    }
                    ret.push([test.uri.fsPath, data.testInfo.name]);
                }
                return ret;
            }

            envFiltering = JSON.stringify({
                "include": convertToFiltering(includeTests),
                "exclude": convertToFiltering(excludeTests),
            });
        }

        for (const test of testCases) {
            const data = testData.get(test);
            if (data === undefined) {
                OUTPUT_CHANNEL.appendLine("Unable to get data for: " + test.id);
                continue;
            }
            targets.add(test.uri.fsPath);
            if (getType(test) == ItemType.TestCase) {
                args.push("-t");
                args.push(data.testInfo.name);
            }
        }

        const targetsAsArray = [];
        for (const t of targets) {
            targetsAsArray.push(t);
        }

        let debugConfiguration: vscode.DebugConfiguration = {
            "type": "robotframework-lsp",
            "runId": runId,
            "name": "Robot Framework: Launch " + runId,
            "request": "launch",
            "cwd": cwd,
            "target": targetsAsArray[0], // TODO: Handle multiple targets.
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

        if (envFiltering !== undefined) {
            if (!debugConfiguration.env) {
                debugConfiguration.env = { "RFLS_PRERUN_FILTER_TESTS": envFiltering };
            } else {
                debugConfiguration.env["RFLS_PRERUN_FILTER_TESTS"] = envFiltering;
            }
        }

        let debugSessionOptions: vscode.DebugSessionOptions = { "noDebug": !shouldDebug };
        let started = await vscode.debug.startDebugging(workspaceFolder, debugConfiguration, debugSessionOptions);
        return started;
    }

    const runProfile = controller.createRunProfile("Run", vscode.TestRunProfileKind.Run, (request, token) => {
        runHandler(false, request, token);
    });

    const debugProfile = controller.createRunProfile("Debug", vscode.TestRunProfileKind.Debug, (request, token) => {
        runHandler(true, request, token);
    });

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
        if (isRelatedSession(event.session)) {
            OUTPUT_CHANNEL.appendLine("Received event: " + event.event + " -- " + JSON.stringify(event.body));
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
                }
            }
        }
    });
}

function handleSuiteStart(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const uriStr = vscode.Uri.file(event.body.source).toString();
    const testNames: string[] = event.body.tests;
    for (const testName of testNames) {
        const testId = computeTestId(uriStr, testName);
        const testItem = testItemIdToTestItem.get(testId);
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
    const testItem = testItemIdToTestItem.get(testId);
    if (!testItem) {
        OUTPUT_CHANNEL.appendLine("Did not find test item: " + testId);
    } else {
        testRun.started(testItem);
    }
}

function failedKeywordsToTestMessage(event: vscode.DebugSessionCustomEvent): vscode.TestMessage[] {
    let messages: vscode.TestMessage[] = [];
    let msg = event.body.message;
    if (!msg) {
        msg = "";
    }
    let failedKeywords = event.body.failed_keywords;
    if (failedKeywords) {
        for (const failed of failedKeywords) {
            // "name": name,
            // "source": source,
            // "lineno": lineno,
            // "failure_messages": self._keyword_failure_messages,
            let errorMsg = "";
            for (const s of failed.failure_messages) {
                errorMsg += s;
            }

            if (failed.source) {
                messages.push({
                    "message": errorMsg,
                    "location": {
                        "uri": vscode.Uri.file(failed.source),
                        "range": new vscode.Range(
                            new vscode.Position(failed.lineno - 1, 0),
                            new vscode.Position(failed.lineno - 1, 0)
                        ),
                    },
                });
            } else {
                if (msg.length == 0) {
                    msg += "\n";
                }
                msg += errorMsg;
            }
        }
    }
    messages.push({
        "message": msg,
    });
    return messages;
}

function handleSuiteEnd(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const uriStr = vscode.Uri.file(event.body.source).toString();
    const testItem = testItemIdToTestItem.get(uriStr);
    markTestRun(testItem, uriStr, testRun, event);
}

function handleTestEnd(testRun: vscode.TestRun, event: vscode.DebugSessionCustomEvent) {
    const testUriStr = vscode.Uri.file(event.body.source).toString();
    const testName = event.body.name;
    const testId = computeTestId(testUriStr, testName);
    const testItem = testItemIdToTestItem.get(testId);
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
                testRun.failed(testItem, failedKeywordsToTestMessage(event), event.body.elapsedtime);
                break;
            default:
                testRun.errored(testItem, failedKeywordsToTestMessage(event), event.body.elapsedtime);
                break;
        }
    }
}
