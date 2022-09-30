import * as path from "path";
import * as fs from "fs";
import * as AdmZip from "adm-zip";
import * as rimraf from 'rimraf'

import { window, Progress, ProgressLocation, CancellationToken } from "vscode";
import { getExtensionRelativeFile, readFromFile, verifyFileExists, writeToFile } from "./files";
import { download } from "./rcc";
import { getHome } from "./robocorpSettings";

export const CONVERSION_STATUS = {
    alreadyCheckedVersion: false,
};

export const ROBOCORP_COMMONS_STATUS = {
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

export async function ensureConvertBundle(): Promise<string> {
    const bundleURL = "https://downloads.robocorp.com/converter/latest/bundle.js";
    const bundleRelativeLocation = "../../vscode-client/out/converterBundle.js";
    const bundleLocation = getExtensionRelativeFile(bundleRelativeLocation, false);

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

    // if the bundle file doesn't exit or isn't marked as being downloaded, force download
    const warnUser: boolean = false;
    if (!verifyFileExists(bundleLocation, warnUser)) {
        await downloadBundle();
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
            if (!shouldUpgrade || shouldUpgrade === "No") {
                // do not continue with download & use current version
                return bundleLocation;
            }
            await writeToFile(currentVersionLocation, newVersion);
            await downloadBundle();
        }
    }
    return bundleLocation;
}


export const getRobocorpCommonsVersion = async (): Promise<{
    currentVersion?: string;
    newVersion?: string;
    currentVersionLocation?: string;
}> => {
    const versionURL = "https://downloads.robocorp.com/converter/commons/version.txt";
    const currentVersionLocation = getExtensionRelativeFile("../../vscode-client/out/robocorp-bp-commons.version", false);
    const newVersionLocation = getExtensionRelativeFile("../../vscode-client/out/robocorp-bp-commons.version.new", false);

    const currentVersion = await readFromFile(currentVersionLocation);
    let newVersion = undefined;
    await window.withProgress(
        {
            location: ProgressLocation.Notification,
            title: "Checking Robocorp commons version",
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


export async function ensureRobocorpCommons(): Promise<string | undefined> {
    const converterHome = path.join(getHome(), 'converter');
    const robocorpBpCommonLocation = path.join(converterHome, 'robocorp-bp-common');

    // common zip
    const commonsURL = "https://downloads.robocorp.com/converter/commons/robocorp-bp-commons.zip";
    const commonsZipRelativeLocation = "../../vscode-client/out/robocorp-bp-commons.zip";
    const commonZipLocation = getExtensionRelativeFile(commonsZipRelativeLocation, false);

    // location of convert.yaml
    const convertYamlLocation = path.join(robocorpBpCommonLocation, 'convert.yaml');

    const downloadCommons = async () =>
        await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: "Downloading Robocorp commons",
                cancellable: false,
            },
            async (
                progress: Progress<{ message?: string; increment?: number }>,
                token: CancellationToken
            ): Promise<string | undefined> => await download(commonsURL, progress, token, commonZipLocation)
        );

    const unzipCommons = async () =>
        await window.withProgress(
            {
                location: ProgressLocation.Notification,
                title: "Unzipping Robocorp commons",
                cancellable: false,
            },
            async (
                progress: Progress<{ message?: string; increment?: number }>,
                token: CancellationToken
            ): Promise<void> => {
                if (verifyFileExists(robocorpBpCommonLocation, false)) {
                    rimraf.sync(robocorpBpCommonLocation)
                }

                await fs.promises.mkdir(robocorpBpCommonLocation, { recursive: true });

                const zip = new AdmZip(commonZipLocation);
                zip.extractAllTo(robocorpBpCommonLocation);
            } 
        );

    if (!verifyFileExists(convertYamlLocation, false)) {
        await downloadCommons();
        await unzipCommons();
    } else if (!ROBOCORP_COMMONS_STATUS.alreadyCheckedVersion) {
        ROBOCORP_COMMONS_STATUS.alreadyCheckedVersion = true;
        const { currentVersion, newVersion, currentVersionLocation } = await getRobocorpCommonsVersion();
        if (currentVersion && newVersion && currentVersion !== newVersion) {
            // ask user if we should download the new version of the commons or use old one
            const items = ["Yes", "No"];
            const shouldUpgrade = await window.showQuickPick(items, {
                "placeHolder": `Would you like to update Robocorp commons to version: ${newVersion}?`,
                "canPickMany": false,
                "ignoreFocusOut": true,
            });
            if (shouldUpgrade && shouldUpgrade !== "No") {
                await writeToFile(currentVersionLocation, newVersion);
                await downloadCommons();
                await unzipCommons();
            }
           
        }
    }

    if (!verifyFileExists(convertYamlLocation, false)) {
        // something bad happened, just return undefined
        // in this way the converter won't try to use any common model
        return undefined;
    }

    return convertYamlLocation;
}
