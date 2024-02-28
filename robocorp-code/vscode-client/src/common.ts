import { LocalRobotMetadataInfo } from "./protocols";

export const debounce = (func, wait) => {
    let timeout: NodeJS.Timeout;

    return function wrapper(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };

        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

export interface PackageEntry {
    filePath: string;
}

export const isActionPackage = (entry: PackageEntry | LocalRobotMetadataInfo) => {
    return entry.filePath.endsWith("package.yaml");
};
