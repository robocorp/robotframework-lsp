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
                id="robocorp-robots-tree",
                name="Robots",
                contextual_title="Robots",
                menus={
                    # See: https://code.visualstudio.com/api/references/contribution-points#contributes.menus
                    # for targets
                    "view/title": [
                        Menu("robocorp.refreshRobotsView", MenuGroup.NAVIGATION),
                        Menu("robocorp.createRobot", MenuGroup.NAVIGATION),
                    ],
                    "view/item/context": [
                        Menu(
                            "robocorp.robotsViewTaskRun",
                            MenuGroup.INLINE,
                            "viewItem == taskItem",
                        ),
                        Menu(
                            "robocorp.robotsViewTaskDebug",
                            MenuGroup.INLINE,
                            "viewItem == taskItem",
                        ),
                        Menu(
                            "robocorp.openRobotTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == robotItem",
                        ),
                        Menu(
                            "robocorp.cloudUploadRobotTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == robotItem",
                        ),
                        Menu(
                            "robocorp.rccTerminalCreateRobotTreeSelection",
                            MenuGroup.INLINE,
                            "viewItem == robotItem",
                        ),
                        # Needs right click (duplicating above + new actions)
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
                id="robocorp-robot-content-tree",
                name="Robot Content",
                contextual_title="Robot Content",
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
                id="robocorp-locators-tree",
                name="Locators",
                contextual_title="Locators",
                menus={
                    "view/title": [
                        Menu(
                            "robocorp.newRobocorpInspectorBrowser",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.newRobocorpInspectorImage",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.newRobocorpInspectorWindows",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                    ],
                    "view/item/context": [
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
                    ],
                },
            ),
            TreeView(
                id="robocorp-work-items-tree",
                name="Work Items",
                contextual_title="Work Items",
                menus={
                    "view/title": [
                        Menu(
                            "robocorp.newWorkItemInWorkItemsView",
                            MenuGroup.NAVIGATION,
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.helpWorkItems",
                            MenuGroup.NAVIGATION,
                            when="robocorp-code:single-robot-selected",
                        ),
                    ],
                    "view/item/context": [
                        Menu(
                            "robocorp.newWorkItemInWorkItemsView",
                            "0_new",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.deleteWorkItemInWorkItemsView",
                            "1_change",
                            when="viewItem == outputWorkItem || viewItem == inputWorkItem",
                        ),
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
                    ],
                },
            ),
            TreeView(
                id="robocorp-cloud-tree",
                name="Robocorp",
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
                            "robocorp.connectVault",
                            MenuGroup.INLINE,
                            when="viewItem == vaultDisconnected",
                        ),
                        Menu(
                            "robocorp.disconnectVault",
                            MenuGroup.INLINE,
                            when="viewItem == vaultConnected",
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
    return {"activitybar": activity_bar_contents}


def get_tree_views_for_package_json():
    ret = {}

    for tree_view_container in TREE_VIEW_CONTAINERS:
        ret[tree_view_container.id] = [
            {"id": tree.id, "name": tree.name, "contextualTitle": tree.contextual_title}
            for tree in tree_view_container.tree_views
            if tree.add_to_package_json
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
