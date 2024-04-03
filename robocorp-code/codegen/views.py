import enum
from typing import Optional, Union


class TreeView:
    def __init__(self, id, name, contextual_title, menus, add_to_package_json=True):
        self.id = id
        self.name = name
        self.contextual_title = contextual_title
        self.menus = menus
        self.add_to_package_json = add_to_package_json


class TreeViewContainer:
    def __init__(self, id, title, icon, tree_views):
        self.id = id
        self.title = title
        self.icon = icon
        self.tree_views = tree_views


class MenuGroup(enum.Enum):
    # https://code.visualstudio.com/api/references/contribution-points#contributes.menus
    NAVIGATION = "navigation"
    INLINE = "inline"


class Menu:
    def __init__(
        self,
        command_id,
        group: Optional[Union[MenuGroup, str]] = None,
        when: Optional[str] = None,
    ):
        self.command_id = command_id
        self.group = group
        self.when = when


TREE_VIEW_CONTAINERS = [
    TreeViewContainer(
        id="robocorp-robots",
        title="Robocorp Code",
        icon="images/robocorp-outline.svg",
        tree_views=[
            TreeView(
                id="robocorp-task-packages-tree",
                name="Task/Action Packages",
                contextual_title="Task/Action Packages",
                menus={
                    # See: https://code.visualstudio.com/api/references/contribution-points#contributes.menus
                    # for targets
                    "view/title": [
                        Menu("robocorp.refreshRobotsView", MenuGroup.NAVIGATION),
                        Menu(
                            "robocorp.createTaskOrActionPackage", MenuGroup.NAVIGATION
                        ),
                    ],
                    "view/item/context": [
                        # Task run as context menus
                        Menu(
                            "robocorp.robotsViewTaskRun",
                            "inline@1",
                            "viewItem == taskItem",
                        ),
                        Menu(
                            "robocorp.robotsViewTaskDebug",
                            "inline@2",
                            "viewItem == taskItem",
                        ),
                        # Action run as context menus
                        Menu(
                            "robocorp.robotsViewActionOpen",
                            "inline@1",
                            "viewItem == actionItem",
                        ),
                        Menu(
                            "robocorp.robotsViewActionEditInput",
                            "inline@2",
                            "viewItem == actionItem",
                        ),
                        Menu(
                            "robocorp.robotsViewActionRun",
                            "inline@3",
                            "viewItem == actionItem",
                        ),
                        Menu(
                            "robocorp.robotsViewActionDebug",
                            "inline@4",
                            "viewItem == actionItem",
                        ),
                        # Inline in actions
                        Menu(
                            "robocorp.openRobotTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == actionsInRobotItem",
                        ),
                        Menu(
                            "robocorp.openRobotCondaTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == actionsInRobotItem",
                        ),
                        Menu(
                            "robocorp.rccTerminalCreateRobotTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == actionsInRobotItem",
                        ),
                        Menu(
                            "robocorp.cloudUploadRobotTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == actionsInRobotItem",
                        ),
                        Menu(
                            "robocorp.openFlowExplorerTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == actionsInRobotItem",
                        ),
                        # Tasks: Needs right click (duplicating above + new actions)
                        Menu(
                            "robocorp.robotsViewTaskRun",
                            MenuGroup.NAVIGATION,
                            "viewItem == taskItem",
                        ),
                        Menu(
                            "robocorp.robotsViewTaskDebug",
                            MenuGroup.NAVIGATION,
                            "viewItem == taskItem",
                        ),
                        # Actions: Needs right click (duplicating above + new actions)
                        Menu(
                            "robocorp.robotsViewActionRun",
                            MenuGroup.NAVIGATION,
                            "viewItem == actionItem",
                        ),
                        Menu(
                            "robocorp.robotsViewActionDebug",
                            MenuGroup.NAVIGATION,
                            "viewItem == actionItem",
                        ),
                        Menu(
                            "robocorp.robotsViewActionEditInput",
                            MenuGroup.NAVIGATION,
                            "viewItem == actionItem",
                        ),
                        Menu(
                            "robocorp.robotsViewActionOpen",
                            MenuGroup.NAVIGATION,
                            "viewItem == actionItem",
                        ),
                        # New action: reveal in explorer.
                        Menu(
                            "robocorp.revealRobotInExplorer",
                            MenuGroup.NAVIGATION,
                            when="viewItem == robotItem",
                        ),
                        Menu(
                            "robocorp.openRobotTreeSelection",
                            MenuGroup.NAVIGATION,
                            when="viewItem == robotItem",
                        ),
                        Menu(
                            "robocorp.rccTerminalCreateRobotTreeSelection",
                            MenuGroup.NAVIGATION,
                            when="viewItem == robotItem",
                        ),
                        Menu(
                            "robocorp.cloudUploadRobotTreeSelection",
                            MenuGroup.NAVIGATION,
                            when="viewItem == robotItem",
                        ),
                    ],
                },
            ),
            TreeView(
                id="robocorp-package-content-tree",
                name="Package Content",
                contextual_title="Package Content",
                menus={
                    "view/title": [
                        Menu(
                            "robocorp.newFileInRobotContentView",
                            MenuGroup.NAVIGATION,
                            when="robocorp-code:single-robot-selected && viewItem == directoryItem",
                        ),
                        Menu(
                            "robocorp.newFolderInRobotContentView",
                            MenuGroup.NAVIGATION,
                            when="robocorp-code:single-robot-selected && viewItem == directoryItem",
                        ),
                        Menu("robocorp.refreshRobotContentView", MenuGroup.NAVIGATION),
                    ],
                    "view/item/context": [
                        Menu(
                            "robocorp.newFileInRobotContentView",
                            "0_new",
                            when="robocorp-code:single-robot-selected && viewItem == directoryItem",
                        ),
                        Menu(
                            "robocorp.newFolderInRobotContentView",
                            "0_new",
                            when="robocorp-code:single-robot-selected && viewItem == directoryItem",
                        ),
                        Menu(
                            "robocorp.openExternally",
                            "1_open",
                            when="robocorp-code:single-robot-selected && viewItem == fileItem",
                        ),
                        Menu(
                            "robocorp.openInVSCode",
                            "1_open",
                            when="robocorp-code:single-robot-selected && viewItem == fileItem",
                        ),
                        Menu(
                            "robocorp.revealInExplorer",
                            "1_open",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.renameResourceInRobotContentView",
                            "2_change",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.deleteResourceInRobotContentView",
                            "2_change",
                            when="robocorp-code:single-robot-selected",
                        ),
                    ],
                },
            ),
            TreeView(
                id="robocorp-package-resources-tree",
                name="Package Resources",
                contextual_title="Package Resources",
                menus={
                    "view/item/context": [
                        # Locators (root)
                        Menu(
                            "robocorp.newRobocorpInspectorBrowser",
                            MenuGroup.INLINE,
                            "robocorp-code:single-robot-selected && viewItem == newBrowserLocator",
                        ),
                        Menu(
                            "robocorp.newRobocorpInspectorWindows",
                            MenuGroup.INLINE,
                            "robocorp-code:single-robot-selected && viewItem == newWindowsLocator",
                        ),
                        Menu(
                            "robocorp.newRobocorpInspectorImage",
                            MenuGroup.INLINE,
                            "robocorp-code:single-robot-selected && viewItem == newImageLocator",
                        ),
                        Menu(
                            "robocorp.newRobocorpInspectorJava",
                            MenuGroup.INLINE,
                            "robocorp-code:single-robot-selected && viewItem == newJavaLocator",
                        ),
                        # Locators (root)
                        Menu(
                            "robocorp.openLocatorsJson",
                            MenuGroup.INLINE,
                            "viewItem == locatorsRoot",
                        ),
                        # Locators (entries)
                        Menu(
                            "robocorp.editRobocorpInspectorLocator",
                            MenuGroup.INLINE,
                            when="robocorp-code:single-robot-selected && viewItem == locatorEntry",
                        ),
                        Menu(
                            "robocorp.copyLocatorToClipboard.internal",
                            MenuGroup.INLINE,
                            when="robocorp-code:single-robot-selected && viewItem == locatorEntry",
                        ),
                        Menu(
                            "robocorp.removeLocatorFromJson",
                            MenuGroup.INLINE,
                            when="robocorp-code:single-robot-selected && viewItem == locatorEntry",
                        ),
                        # Work items (root)
                        Menu(
                            "robocorp.helpWorkItems",
                            MenuGroup.INLINE,
                            when="robocorp-code:single-robot-selected && viewItem == workItemsRoot",
                        ),
                        # Work items (new)
                        Menu(
                            "robocorp.newWorkItemInWorkItemsView",
                            MenuGroup.INLINE,
                            when="robocorp-code:single-robot-selected && viewItem == inputWorkItemDir",
                        ),
                        # Work items (entries)
                        Menu(
                            "robocorp.deleteWorkItemInWorkItemsView",
                            MenuGroup.INLINE,
                            when="viewItem == outputWorkItem || viewItem == inputWorkItem",
                        ),
                        Menu(
                            "robocorp.convertOutputWorkItemToInput",
                            MenuGroup.INLINE,
                            when="viewItem == outputWorkItem",
                        ),
                    ]
                },
            ),
            TreeView(
                id="robocorp-cloud-tree",
                name="Robocorp Cloud",
                contextual_title="Robocorp",
                menus={
                    "view/item/context": [
                        Menu(
                            "robocorp.cloudLogin",
                            MenuGroup.INLINE,
                            when="viewItem == cloudLoginItem",
                        ),
                        Menu(
                            "robocorp.cloudLogout",
                            MenuGroup.INLINE,
                            when="viewItem == cloudLogoutItem",
                        ),
                        Menu(
                            "robocorp.openCloudHome",
                            MenuGroup.INLINE,
                            when="viewItem == cloudLogoutItem",
                        ),
                        Menu(
                            "robocorp.connectWorkspace",
                            MenuGroup.INLINE,
                            when="viewItem == workspaceDisconnected",
                        ),
                        Menu(
                            "robocorp.disconnectWorkspace",
                            MenuGroup.INLINE,
                            when="viewItem == workspaceConnected",
                        ),
                        Menu(
                            "robocorp.profileImport",
                            MenuGroup.INLINE,
                            when="viewItem == profileItem",
                        ),
                        Menu(
                            "robocorp.profileSwitch",
                            MenuGroup.INLINE,
                            when="viewItem == profileItem",
                        ),
                    ]
                },
            ),
        ],
    )
]


def get_views_containers():
    activity_bar_contents = [
        {
            "id": tree_view_container.id,
            "title": tree_view_container.title,
            "icon": tree_view_container.icon,
        }
        for tree_view_container in TREE_VIEW_CONTAINERS
    ]
    return {
        "activitybar": activity_bar_contents,
        "panel": [
            {
                "id": "robocorp-python-view-output",
                "title": "Robo Tasks Output",
                "icon": "$(output)",
            },
        ],
    }


def get_tree_views_for_package_json():
    ret = {}

    for tree_view_container in TREE_VIEW_CONTAINERS:
        ret[tree_view_container.id] = [
            {"id": tree.id, "name": tree.name, "contextualTitle": tree.contextual_title}
            for tree in tree_view_container.tree_views
            if tree.add_to_package_json
        ]

    ret["robocorp-python-view-output"] = [
        {
            "type": "webview",
            "id": "robocorp.python.view.output",
            "name": "Robo Tasks Output",
            "contextualTitle": "Robo Tasks Output",
        }
    ]

    return ret


def get_activation_events_for_json():
    activation_events = []

    for tree_view_container in TREE_VIEW_CONTAINERS:
        for tree_viewer in tree_view_container.tree_views:
            if not tree_viewer.add_to_package_json:
                continue
            activation_events.append("onView:" + tree_viewer.id)

    return activation_events


def get_menus():
    menus = {}

    for tree_view_container in TREE_VIEW_CONTAINERS:
        for tree_viewer in tree_view_container.tree_views:
            if not tree_viewer.add_to_package_json:
                continue
            menu: Menu
            for menu_id, menu_lst in tree_viewer.menus.items():
                for menu in menu_lst:
                    when = f"view == {tree_viewer.id}"
                    if menu.when:
                        when += f" && {menu.when}"
                    item = {"command": menu.command_id, "when": when}
                    if menu.group:
                        if isinstance(menu.group, str):
                            item["group"] = menu.group
                        else:
                            item["group"] = menu.group.value
                    menus.setdefault(menu_id, []).append(item)

    return menus
