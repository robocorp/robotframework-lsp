import * as AdmZip from "adm-zip";
import * as rimraf from "rimraf";

import * as path from "path";

import { window, Progress, ProgressLocation, CancellationToken, Uri, workspace } from "vscode";
import {
    fileExists,
    findNextBasenameIn,
    getExtensionRelativeFile,
    makeDirs,
    readFromFile,
    verifyFileExists,
    writeToFile,
} from "./files";
import { download, feedback, Metrics } from "./rcc";
import { basename, join } from "path";
import { logError, OUTPUT_CHANNEL } from "./channel";
import { TextDecoder } from "util";
import {
    CommandType,
    ConversionFailure,
    ConversionResult,
    ConversionSuccess,
    Format,
    isSuccessful,
    RPAConversionCommand,
} from "./protocols";
import { readdirSync, rmSync, statSync, existsSync } from "fs";

export const CONVERSION_STATUS = {
    alreadyCheckedVersion: false,
};

export enum RPATypes {
    uipath = "uipath",
    blueprism = "blueprism",
    a360 = "a360",
    aav11 = "aav11",
}

export const RPA_TYPE_TO_CAPTION = {
    "uipath": "UiPath",
    "blueprism": "Blue Prism",
    "a360": "Automation Anywhere 360",
    "aav11": "Automation Anywhere 11",
};

export async function conversionMain(converterBundle, command: RPAConversionCommand): Promise<ConversionResult> {
    return await converterBundle.main(command);
}

export const getConverterBundleVersion = async (): Promise<{
    currentVersion?: string;
    newVersion?: string;
    currentVersionLocation?: string;
}> => {
    const versionURL = "https://downloads.robocorp.com/converter/latest/version-with-commons.txt";
    const currentVersionLocation = getExtensionRelativeFile("../../vscode-client/out/converterBundle.version", false);
    const newVersionLocation = getExtensionRelativeFile("../../vscode-client/out/converterBundle.version.new", false);

    // downloading & reading the new version
    const currentVersion = await readFromFile(currentVersionLocation);
    let newVersion = undefined;
    await window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Checking converter version",
            cancellable: false,
        },
        async (
            progress: Progress<{ message?: string; increment?: number }>,
            token: CancellationToken
        ): Promise<string | undefined> => {
            const result = await download(
                versionURL,
                progress,
                token,
                currentVersion ? newVersionLocation : currentVersionLocation
            );
            newVersion = await readFromFile(currentVersion ? newVersionLocation : currentVersionLocation);
            return result;
        }
    );
    return { currentVersion: currentVersion, newVersion: newVersion, currentVersionLocation: currentVersionLocation };
};

export async function ensureConvertBundle(): Promise<{
    pathToExecutable: string;
    pathToConvertYaml?: string;
}> {
    const bundleURL = "https://downloads.robocorp.com/converter/latest/converter-with-commons.zip";
    const bundleRelativeLocation = "../../vscode-client/out/converter-with-commons.zip";
    const bundleLocation = getExtensionRelativeFile(bundleRelativeLocation, false);
    const bundleFolderRelativeLocation = "../../vscode-client/out/converter-with-commons";
    const bundleFolderLocation = getExtensionRelativeFile(bundleFolderRelativeLocation, false);

    // downloading the bundle
    const downloadBundle = async () =>
        await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: "Downloading converter bundle",
                cancellable: false,
            },
            async (
                progress: Progress<{ message?: string; increment?: number }>,
                token: CancellationToken
            ): Promise<string | undefined> => await download(bundleURL, progress, token, bundleLocation)
        );

    const unzipBundle = async () => {
        // remove previous bundle if it exists
        if (verifyFileExists(bundleFolderLocation, false)) {
            rimraf.sync(bundleFolderLocation);
        }

        const zip = new AdmZip(bundleLocation);
        zip.extractAllTo(bundleFolderLocation);
    };

    // if the bundle file doesn't exit or isn't marked as being downloaded, force download
    const warnUser: boolean = false;
    if (!verifyFileExists(bundleLocation, warnUser)) {
        await downloadBundle();
        await unzipBundle();
    } else if (!CONVERSION_STATUS.alreadyCheckedVersion) {
        CONVERSION_STATUS.alreadyCheckedVersion = true;
        const { currentVersion, newVersion, currentVersionLocation } = await getConverterBundleVersion();
        if (currentVersion && newVersion && currentVersion !== newVersion) {
            // ask user if we should download the new version of the bundle or use old one
            const items = ["Yes", "No"];
            const shouldUpgrade = await window.showQuickPick(items, {
                "placeHolder": `Would you like to update the converter to version: ${newVersion}?`,
                "canPickMany": false,
                "ignoreFocusOut": true,
            });
            if (shouldUpgrade && shouldUpgrade !== "No") {
                await writeToFile(currentVersionLocation, newVersion);
                await downloadBundle();
                await unzipBundle();
            }
        }
    }

    const executable = path.join(bundleFolderLocation, "bundle.js");
    const convertYaml = path.join(bundleFolderLocation, "robocorp-commons", "convert.yaml");

    return {
        pathToExecutable: executable,
        pathToConvertYaml: verifyFileExists(convertYaml) ? convertYaml : undefined,
    };
}

export async function convertAndSaveResults(
    convertBundlePromise: Promise<{
        pathToExecutable: string;
        pathToConvertYaml?: string;
    }>,
    opts: {
        inputType: RPATypes;
        input: string[];
        outputFolder: string;
        targetLanguage: string;
        adapterFolderPath: string;
    }
): Promise<{
    success: boolean;
    message: string;
}> {
    const converterLocation = await convertBundlePromise;
    if (!converterLocation) {
        return {
            "success": false,
            "message": "There was an issue downloading the converter bundle. Please try again.",
        };
    }
    const converterBundle = require(converterLocation.pathToExecutable);
    let rpaConversionCommands: RPAConversionCommand[] = [];

    if (!opts.input || opts.input.length === 0) {
        return {
            "success": false,
            "message": "Unable to do conversion because input was not specified.",
        };
    }

    // We want to create a structure such as:
    //
    // Just for conversions:
    // /output_folder/converted-uipath/...
    // /output_folder/converted-uipath-1/...
    // ...
    //
    // For analysis + conversion:
    // /output_folder/converted-uipath-1/analysis
    // /output_folder/converted-uipath-1/generated

    const cleanups = [];

    feedback(Metrics.CONVERTER_USED, opts.inputType);

    try {
        let nextBasename: string;
        const targetLanguage = opts.targetLanguage;
        switch (opts.inputType) {
            case RPATypes.uipath: {
                nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-uipath");
                const projects: Array<string> = opts.input;
                const tempDir: string = join(opts.outputFolder, nextBasename, "temp");
                await makeDirs(tempDir);

                cleanups.push(() => {
                    try {
                        rmSync(tempDir, { recursive: true, force: true, maxRetries: 1 });
                    } catch (err) {
                        OUTPUT_CHANNEL.appendLine("Error deleting: " + tempDir + ": " + err.message);
                    }
                });

                rpaConversionCommands.push({
                    command: CommandType.Schema,
                    vendor: Format.UIPATH,
                    projects: projects,
                    onProgress: undefined,
                    outputRelativePath: join(nextBasename, "schema"),
                });

                rpaConversionCommands.push({
                    command: CommandType.Analyse,
                    vendor: Format.UIPATH,
                    projects: projects,
                    onProgress: undefined,
                    tempFolder: tempDir,
                    outputRelativePath: join(nextBasename, "analysis"),
                });
                for (const it of opts.input) {
                    rpaConversionCommands.push({
                        vendor: Format.UIPATH,
                        command: CommandType.Convert,
                        projectFolderPath: it,
                        targetLanguage,
                        onProgress: undefined,
                        outputRelativePath: join(nextBasename, basename(it)),
                    });
                }
                break;
            }
            case RPATypes.blueprism: {
                nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-blueprism");
                const projects: Array<string> = opts.input;
                const tempDir: string = join(opts.outputFolder, nextBasename, "temp");
                await makeDirs(tempDir);

                cleanups.push(() => {
                    try {
                        rmSync(tempDir, { recursive: true, force: true, maxRetries: 1 });
                    } catch (err) {
                        OUTPUT_CHANNEL.appendLine("Error deleting: " + tempDir + ": " + err.message);
                    }
                });
                rpaConversionCommands.push({
                    command: CommandType.Analyse,
                    vendor: Format.BLUEPRISM,
                    projects: projects,
                    onProgress: undefined,
                    tempFolder: tempDir,
                    outputRelativePath: join(nextBasename, "analysis"),
                });
                for (const it of opts.input) {
                    let contents = "";
                    try {
                        if (!(await fileExists(it))) {
                            return {
                                "success": false,
                                "message": `${it} does not exist.`,
                            };
                        }
                        const uri = Uri.file(it);
                        const bytes = await workspace.fs.readFile(uri);
                        contents = new TextDecoder("utf-8").decode(bytes);
                    } catch (err) {
                        const message = "Unable to read: " + it + "\n" + err.message;
                        logError(message, err, "ERROR_READ_BLUEPRISM_FILE");
                        return {
                            "success": false,
                            "message": message,
                        };
                    }

                    rpaConversionCommands.push({
                        vendor: Format.BLUEPRISM,
                        command: CommandType.Convert,
                        releaseFileContent: contents,
                        apiImplementationFolderPath: converterLocation.pathToConvertYaml,
                        targetLanguage,
                        onProgress: undefined,
                        outputRelativePath: join(nextBasename, basename(it)),
                    });
                }
                break;
            }
            case RPATypes.a360: {
                nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-a360");
                const projects: Array<string> = opts.input;
                const tempDir: string = join(opts.outputFolder, nextBasename, "temp");
                await makeDirs(tempDir);

                cleanups.push(() => {
                    try {
                        rmSync(tempDir, { recursive: true, force: true, maxRetries: 1 });
                    } catch (err) {
                        OUTPUT_CHANNEL.appendLine("Error deleting: " + tempDir + ": " + err.message);
                    }
                });

                rpaConversionCommands.push({
                    command: CommandType.Schema,
                    vendor: Format.A360,
                    projects: projects,
                    onProgress: undefined,
                    outputRelativePath: join(nextBasename, "schema"),
                });
                rpaConversionCommands.push({
                    command: CommandType.Analyse,
                    vendor: Format.A360,
                    projects: projects,
                    onProgress: undefined,
                    tempFolder: tempDir,
                    outputRelativePath: join(nextBasename, "analysis"),
                });

                const adapterFilePaths = [];
                if (existsSync(opts.adapterFolderPath)) {
                    const stat = statSync(opts.adapterFolderPath);
                    if (stat.isDirectory()) {
                        const files = readdirSync(opts.adapterFolderPath);
                        for (const file of files) {
                            const filepath = path.join(opts.adapterFolderPath, file);
                            const fileStat = statSync(filepath);
                            if (fileStat.isFile()) {
                                adapterFilePaths.push(filepath);
                            }
                        }
                    }
                }

                for (const it of opts.input) {
                    rpaConversionCommands.push({
                        vendor: Format.A360,
                        command: CommandType.Convert,
                        projectFolderPath: it,
                        adapterFilePaths,
                        targetLanguage,
                        onProgress: undefined,
                        outputRelativePath: join(nextBasename, basename(it)),
                    });
                }
                break;
            }
            case RPATypes.aav11:
                nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-aav11");
                const projects: Array<string> = opts.input;
                const tempDir: string = join(opts.outputFolder, nextBasename, "temp");
                await makeDirs(tempDir);

                cleanups.push(() => {
                    try {
                        rmSync(tempDir, { recursive: true, force: true, maxRetries: 1 });
                    } catch (err) {
                        OUTPUT_CHANNEL.appendLine("Error deleting: " + tempDir + ": " + err.message);
                    }
                });

                rpaConversionCommands.push({
                    vendor: Format.AAV11,
                    command: CommandType.Analyse,
                    projects: projects,
                    onProgress: undefined,
                    tempFolder: tempDir,
                    outputRelativePath: join(nextBasename, "analysis"),
                });

                rpaConversionCommands.push({
                    vendor: Format.AAV11,
                    command: CommandType.Generate,
                    projects: projects,
                    onProgress: undefined,
                    tempFolder: tempDir,
                    outputRelativePath: join(nextBasename, "api"),
                });

                rpaConversionCommands.push({
                    command: CommandType.Schema,
                    vendor: Format.AAV11,
                    projects: projects,
                    onProgress: undefined,
                    tempFolder: tempDir,
                    outputRelativePath: join(nextBasename, "schema"),
                });

                for (const it of opts.input) {
                    rpaConversionCommands.push({
                        vendor: Format.AAV11,
                        command: CommandType.Convert,
                        projects: [it],
                        onProgress: undefined,
                        targetLanguage,
                        tempFolder: tempDir,
                        outputRelativePath: join(nextBasename, "conversion", basename(it)),
                    });
                }
                break;
        }

        return await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: `${RPA_TYPE_TO_CAPTION[opts.inputType]} conversion`,
                cancellable: true,
            },

            async (progress: Progress<{ message?: string; increment?: number }>, token: CancellationToken) => {
                const COMMAND_TO_LABEL = {
                    "Generate": "Generate API",
                    "Convert": "Convert",
                    "Analyse": "Analyse",
                    "Schema": "Generate Schema",
                };
                // If we got here, things worked, let's write it to the filesystem.
                const outputDirsWrittenTo = new Set<string>();

                const results: ConversionResult[] = [];
                const steps: number = rpaConversionCommands.length;
                const errors: Array<[RPAConversionCommand, string]> = [];
                let incrementStep: number = 0;
                let currStep: number = 0;

                // execute commands in sequence, but not fail all if one fails
                for (const command of rpaConversionCommands) {
                    currStep += 1;
                    progress.report({
                        message: `Step (${currStep}/${steps}): ${COMMAND_TO_LABEL[command.command]}`,
                        increment: incrementStep,
                    });
                    incrementStep = 100 / steps;
                    // Give the UI a chance to show the progress.
                    await new Promise((r) => setTimeout(r, 5));

                    const conversionResult: ConversionResult = await conversionMain(converterBundle, command);

                    if (!isSuccessful(conversionResult)) {
                        const message = (<ConversionFailure>conversionResult).error;
                        logError(
                            `Error processing ${command.command} command`,
                            new Error(message),
                            "EXT_CONVERT_PROJECT"
                        );
                        feedback(Metrics.CONVERTER_ERROR, command.vendor);
                        errors.push([command, message]);

                        // skip and process next command
                        continue;
                    }
                    conversionResult.outputDir = join(opts.outputFolder, command.outputRelativePath);
                    results.push(conversionResult);

                    if (token.isCancellationRequested) {
                        return {
                            "success": false,
                            "message": "Operation cancelled.",
                        };
                    }
                }

                const filesWritten: string[] = [];

                async function handleOutputFile(
                    file: string,
                    content: string,
                    encoding: BufferEncoding = "utf-8"
                ): Promise<void> {
                    filesWritten.push(file);
                    const { dir } = path.parse(file);
                    if (dir) {
                        await makeDirs(dir);
                    }
                    await writeToFile(file, content, { encoding });
                }

                const tasks: Promise<void>[] = [];
                for (const result of results) {
                    const okResult: ConversionSuccess = <ConversionSuccess>result;
                    const files = okResult?.files;

                    await makeDirs(result.outputDir);
                    outputDirsWrittenTo.add(result.outputDir);
                    if (files && files.length > 0) {
                        for (const f of files) {
                            tasks.push(
                                handleOutputFile(
                                    join(result.outputDir, f.filename),
                                    f.content,
                                    f.encoding as BufferEncoding
                                )
                            );
                        }
                    }
                }

                await Promise.all(tasks);

                progress.report({ increment: incrementStep });

                const outputDirsWrittenToStr: string[] = [];
                for (const s of outputDirsWrittenTo) {
                    outputDirsWrittenToStr.push(s);
                }
                const d: Date = new Date();

                const readmePath = join(opts.outputFolder, nextBasename, "README.md");
                await writeToFile(
                    readmePath,
                    `Generated: ${d.toISOString()}
----------------------------------

Sources
----------------------------------
${opts.input.join("\n")}

Created Directories
----------------------------------
${outputDirsWrittenToStr.join("\n")}

Created Files
----------------------------------
${filesWritten.join("\n")}

Errors
----------------------------------
${
    errors.length > 0
        ? errors.map(([cmd, error]) => `Cannot process command ${cmd.command}, reason ${error}`).join("\n")
        : "No errors"
}
`
                );

                while (cleanups.length > 0) {
                    const c = cleanups.pop();
                    c.call();
                }

                return {
                    "success": false,
                    "message":
                        `Conversion succeeded.\n\nFinished: ${d.toISOString()}.\n\nWritten to directories:\n\n` +
                        outputDirsWrittenToStr.join("\n"),
                };
            }
        );
    } finally {
        for (const c of cleanups) {
            c.call();
        }
    }
}
