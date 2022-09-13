interface LocalRobotMetadataInfo {
    name: string;
    directory: string;
    filePath: string;
    yamlContents: object;
}

interface IVaultInfo {
    workspaceId: string;
    organizationName: string;
    workspaceName: string;
}

interface WorkspaceInfo {
    organizationName: string;
    workspaceName: string;
    workspaceId: string;
    packages: PackageInfo[];
}

interface PackageInfo {
    workspaceId: string;
    workspaceName: string;
    id: string;
    name: string;
    sortKey: string;
}

interface IAccountInfo {
    fullname: string;
    email: string;
}

interface ActionResult<T> {
    success: boolean;
    message: string;
    result: T;
}

interface InterpreterInfo {
    pythonExe: string;
    environ?: { [key: string]: string };
    additionalPythonpathEntries: string[];
}

interface ListWorkspacesActionResult {
    success: boolean;
    message: string;
    result: WorkspaceInfo[];
}

interface RobotTemplate {
    name: string;
    description: string;
}

interface WorkItem {
    name: string;
    json_path: string;
}

interface WorkItemsInfo {
    robot_yaml: string; // Full path to the robot which has these work item info

    // Full path to the place where input work items are located
    input_folder_path?: string;

    // Full path to the place where output work items are located
    output_folder_path?: string;

    input_work_items: WorkItem[];
    output_work_items: WorkItem[];

    new_output_workitem_path: string;
}

interface ActionResultWorkItems {
    success: boolean;
    message: string;
    result?: WorkItemsInfo;
}

interface LibraryVersionDict {
    library: string;
    version: string;
}

interface LibraryVersionInfoDict {
    success: boolean;

    // if success == False, this can be some message to show to the user
    message?: string;

    //Note that if the library was found but the version doesn't match, the
    // result should still be provided.
    result?: LibraryVersionDict;
}
