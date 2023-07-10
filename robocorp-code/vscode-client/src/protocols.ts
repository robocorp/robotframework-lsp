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

export interface LibraryVersionInfoDict {
    success: boolean;

    // if success == False, this can be some message to show to the user
    message?: string;
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
    encoding?: string;
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
    Schema = "Schema",
}

export interface A360ConvertCommand {
    command: CommandType.Convert;
    vendor: Format.A360;
    projectFolderPath: string;
    targetLanguage: string;
    adapterFilePaths: Array<string>;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface A360SchemaCommand {
    command: CommandType.Schema;
    vendor: Format.A360;
    projects: Array<string>;
    /** properties that should be considered as ENUM  */
    types?: Array<string>;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface A360AnalyseCommand {
    command: CommandType.Analyse;
    vendor: Format.A360;
    projects: Array<string>;
    tempFolder: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface UiPathConvertCommand {
    command: CommandType.Convert;
    vendor: Format.UIPATH;
    projectFolderPath: string;
    targetLanguage: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface UiPathSchemaCommand {
    command: CommandType.Schema;
    vendor: Format.UIPATH;
    projects: Array<string>;
    /** properties that should be considered as ENUM  */
    types?: Array<string>;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface UiPathAnalyseCommand {
    command: CommandType.Analyse;
    vendor: Format.UIPATH;
    projects: Array<string>;
    tempFolder: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface BlueprismConvertCommand {
    command: CommandType.Convert;
    vendor: Format.BLUEPRISM;
    releaseFileContent: string;
    targetLanguage: string;
    apiImplementationFolderPath?: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface BlueprismAnalyseCommand {
    command: CommandType.Analyse;
    vendor: Format.BLUEPRISM;
    projects: Array<string>;
    tempFolder: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface AAV11ConvertCommand {
    command: CommandType.Convert;
    vendor: Format.AAV11;
    /* path to aapkg files */
    projects: Array<string>;
    tempFolder: string;
    targetLanguage: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface AAV11GenerateCommand {
    command: CommandType.Generate;
    vendor: Format.AAV11;
    /* path to aapkg files */
    projects: Array<string>;
    tempFolder: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface AAV11AnalyseCommand {
    command: CommandType.Analyse;
    vendor: Format.AAV11;
    /* path to aapkg files */
    projects: Array<string>;
    tempFolder: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export interface AAV11SchemaCommand {
    command: CommandType.Schema;
    vendor: Format.AAV11;
    /* path to aapkg files */
    projects: Array<string>;
    /** properties that should be considered as ENUM  */
    types?: Array<string>;
    tempFolder: string;
    onProgress: Progress;
    outputRelativePath: string; // Used internally in Robocorp Code
}

export type BlueprismCommand = BlueprismConvertCommand | BlueprismAnalyseCommand;
export type UiPathCommand = UiPathConvertCommand | UiPathSchemaCommand | UiPathAnalyseCommand;
export type A360Command = A360ConvertCommand | A360SchemaCommand | A360AnalyseCommand;
export type AAV11Command = AAV11ConvertCommand | AAV11GenerateCommand | AAV11AnalyseCommand | AAV11SchemaCommand;

export type RPAConversionCommand = BlueprismCommand | UiPathCommand | A360Command | AAV11Command;
