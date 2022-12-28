export interface LocalRobotMetadataInfo {
    name: string;
    directory: string;
    filePath: string;
    yamlContents: object;
}

export interface IVaultInfo {
    workspaceId: string;
    organizationName: string;
    workspaceName: string;
}

export interface WorkspaceInfo {
    organizationName: string;
    workspaceName: string;
    workspaceId: string;
    packages: PackageInfo[];
}

export interface PackageInfo {
    workspaceId: string;
    workspaceName: string;
    id: string;
    name: string;
    sortKey: string;
}

export interface IAccountInfo {
    fullname: string;
    email: string;
}

export interface ActionResult<T> {
    success: boolean;
    message: string;
    result: T;
}

export interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

export interface ListWorkspacesActionResult {
    success: boolean;
    message: string;
    result: WorkspaceInfo[];
}

export interface RobotTemplate {
    name: string;
    description: string;
}

export interface WorkItem {
    name: string;
    json_path: string;
}

export interface WorkItemsInfo {
    robot_yaml: string; // Full path to the robot which has these work item info

    // Full path to the place where input work items are located
    input_folder_path?: string;

    // Full path to the place where output work items are located
    output_folder_path?: string;

    input_work_items: WorkItem[];
    output_work_items: WorkItem[];

    new_output_workitem_path: string;
}

export interface ActionResultWorkItems {
    success: boolean;
    message: string;
    result?: WorkItemsInfo;
}

export interface LibraryVersionDict {
    library: string;
    version: string;
}

export interface LibraryVersionInfoDict {
    success: boolean;

    // if success == False, this can be some message to show to the user
    message?: string;

    //Note that if the library was found but the version doesn't match, the
    // result should still be provided.
    result?: LibraryVersionDict;
}

// these declarations are a superficial variant of the implemented ones in the converter bundle
// they might need changes if the Converter API is changed
export enum ConversionResultType {
    SUCCESS = "Success",
    FAILURE = "Failure",
}

export interface File {
    content: string;
    filename: string;
}

export interface ConversionSuccess {
    type: ConversionResultType.SUCCESS;
    /**
     * @deprecated use files
     */
    robotFileContent: string;
    files: Array<File>;
    report?: File;
    images?: Array<File>;
    outputDir: string; // Used internally in Robocorp Code
}

export interface ConversionFailure {
    type: ConversionResultType.FAILURE;
    error: string;
    report?: File;
    images?: Array<File>;
    outputDir: string; // Used internally in Robocorp Code
}

export type ConversionResult = ConversionSuccess | ConversionFailure;

export function isSuccessful(result: ConversionResult): result is ConversionSuccess {
    return result.type === ConversionResultType.SUCCESS;
}

export enum Format {
    BLUEPRISM = "blueprism",
    A360 = "a360",
    UIPATH = "uipath",
    AAV11 = "aav11",
}

export enum ValidationStatus {
    ValidationSuccess = "ValidationSuccess",
    ValidationError = "ValidationError",
}

export interface ValidationSuccess<T> {
    status: ValidationStatus.ValidationSuccess;
    payload: T;
}

export interface ValidationError {
    status: ValidationStatus.ValidationError;
    messages: string[];
    stack?: string;
}

export type ValidationResult<T> = ValidationSuccess<T> | ValidationError;

export interface Options {
    objectImplFile?: string;
    projectFolderPath?: string;
}

export interface Progress {
    (amount: number, message: string): void;
}

export enum CommandType {
    Analyse = "Analyse",
    Convert = "Convert",
    Generate = "Generate",
}

export interface A360ConvertCommand {
    command: CommandType.Convert;
    vendor: Format.A360;
    projectFolderPath: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface UiPathConvertCommand {
    command: CommandType.Convert;
    vendor: Format.UIPATH;
    projectFolderPath: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface BlueprismConvertCommand {
    command: CommandType.Convert;
    vendor: Format.BLUEPRISM;
    releaseFileContent: string;
    apiImplementationFolderPath?: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface AAV11GenerateCommand {
    command: CommandType.Generate;
    vendor: Format.AAV11;
    folders: Array<string>;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface AAV11AnalyseCommand {
    command: CommandType.Analyse;
    vendor: Format.AAV11;
    folders: Array<string>;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export type BlueprismCommand = BlueprismConvertCommand;
export type UiPathCommand = UiPathConvertCommand;
export type A360Command = A360ConvertCommand;
export type AAV11Command = AAV11GenerateCommand | AAV11AnalyseCommand;

export type RPAConversionCommand = BlueprismCommand | UiPathCommand | A360Command | AAV11Command;
