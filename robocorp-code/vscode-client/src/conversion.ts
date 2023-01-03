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
import { download } from "./rcc";
import { basename, join } from "path";
import { logError } from "./channel";
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

export const CONVERSION_STATUS = {
    alreadyCheckedVersion: false,
};

export enum RPATypes {
    uipath = "uipath",
    blueprism = "blueprism",
    a360 = "a360",
}

export const RPA_TYPE_TO_CAPTION = {
    "uipath": "UiPath",
    "blueprism": "Blue Prism",
    "a360": "Automation Anywhere 360",
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
        apiFolder: string;
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

    let nextBasename: string;
    switch (opts.inputType) {
        case RPATypes.uipath:
            nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-uipath");
            for (const it of opts.input) {
                rpaConversionCommands.push({
                    vendor: Format.UIPATH,
                    command: CommandType.Convert,
                    projectFolderPath: it,
                    onProgress: undefined,
                    outputRelativePath: join(nextBasename, basename(it)),
                });
            }
            break;
        case RPATypes.blueprism:
            nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-blueprism");
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
                    // This isn't added right now because it requires more work (both in explaining to the user as well
                    // as the implementation).
                    // We should collect all the keywords from files in a folder and then merge it with what's available
                    // at converterLocation.pathToConvertYaml and create a new yaml to pass on to the converter.
                    // apiImplementationFolderPath: opts.apiFolder,
                    apiImplementationFolderPath: converterLocation.pathToConvertYaml,
                    onProgress: undefined,
                    outputRelativePath: join(nextBasename, basename(it)),
                });
            }
            break;
        case RPATypes.a360:
            nextBasename = await findNextBasenameIn(opts.outputFolder, "converted-a360");
            for (const it of opts.input) {
                rpaConversionCommands.push({
                    vendor: Format.A360,
                    command: CommandType.Convert,
                    projectFolderPath: it,
                    onProgress: undefined,
                    outputRelativePath: join(nextBasename, basename(it)),
                });
            }
            break;
    }
    const results: ConversionResult[] = [];

    for (const command of rpaConversionCommands) {
        const conversionResult: ConversionResult = await conversionMain(converterBundle, command);
        if (!isSuccessful(conversionResult)) {
            const message = (<ConversionFailure>conversionResult).error;
            logError("Error converting file to Robocorp Robot", new Error(message), "EXT_CONVERT_PROJECT");
            return {
                "success": false,
                "message": message,
            };
        }
        conversionResult.outputDir = join(opts.outputFolder, command.outputRelativePath);
        results.push(conversionResult);
    }

    // If we got here, things worked, let's write it to the filesystem.
    const outputDirsWrittenTo = new Set<string>();
    for (const result of results) {
        const okResult: ConversionSuccess = <ConversionSuccess>result;
        const files = okResult?.files;

        await makeDirs(result.outputDir);
        outputDirsWrittenTo.add(result.outputDir);
        if (files && files.length > 0) {
            for (const f of files) {
                await writeToFile(join(result.outputDir, f.filename), f.content);
            }
        }
        const images = okResult?.images;
        if (images && images.length > 0) {
            for (const f of images) {
                await writeToFile(join(result.outputDir, f.filename), f.content);
            }
        }

        if (okResult.report) {
            await writeToFile(join(result.outputDir, okResult.report.filename), okResult.report.content);
        }
    }

    const outputDirsWrittenToStr = [];
    for (const s of outputDirsWrittenTo) {
        outputDirsWrittenToStr.push(s);
    }

    const d: Date = new Date();
    return {
        "success": false,
        "message":
            `Conversion succeeded.\n\nFinished: ${d.toISOString()}.\n\nWritten to directories:\n\n` +
            outputDirsWrittenToStr.join("\n"),
    };
}
