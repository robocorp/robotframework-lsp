import * as AdmZip from "adm-zip";
import * as rimraf from "rimraf";

import * as path from "path";

import { window, Progress, ProgressLocation, CancellationToken } from "vscode";
import { getExtensionRelativeFile, readFromFile, verifyFileExists, writeToFile } from "./files";
import { download } from "./rcc";

export const CONVERSION_STATUS = {
    alreadyCheckedVersion: false,
};

export const getConverterBundleVersion = async (): Promise<{
    currentVersion?: string;
    newVersion?: string;
    currentVersionLocation?: string;
}> => {
    const versionURL = "https://downloads.robocorp.com/converter/latest/version.txt";
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

    // TODO simplify nesting
    const executable = path.join(bundleFolderLocation, "converter-with-commons", "bundle.js");
    const convertYaml = path.join(bundleFolderLocation, "converter-with-commons", "robocorp-commons", "convert.yaml");

    return {
        pathToExecutable: executable,
        pathToConvertYaml: verifyFileExists(convertYaml) ? convertYaml : undefined,
    };
}
