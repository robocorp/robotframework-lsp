import enum
from typing import Optional, Union
from robocorp_code.commands import ROBOCORP_CLOUD_LOGIN, ROBOCORP_CLOUD_LOGOUT


class TreeView:
    def __init__(self, id, name, contextual_title, menus):
        self.id = id
        self.name = name
        self.contextual_title = contextual_title
        self.menus = menus


class TreeViewContainer:
    def __init__(self, id, title, icon, tree_views):
        self.id = id
        self.title = title
        self.icon = icon
        self.tree_views = tree_views


class MenuGroup(enum.Enum):
    # https://code.visualstudio.com/api/references/contribution-points#contributes.menus
    NAVIGATION = "navigation"


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
                        Menu(
                            "robocorp.robotsViewTaskRun",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-task-selected",
                        ),
                        Menu(
                            "robocorp.robotsViewTaskDebug",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-task-selected",
                        ),
                        Menu(
                            "robocorp.openRobotTreeSelection",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.cloudUploadRobotTreeSelection",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.rccTerminalCreateRobotTreeSelection",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                        Menu("robocorp.refreshRobotsView", MenuGroup.NAVIGATION),
                    ],
                    "view/item/context": [
                        Menu(
                            "robocorp.openRobotTreeSelection",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.cloudUploadRobotTreeSelection",
                            when="robocorp-code:single-robot-selected",
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
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.newFolderInRobotContentView",
                            MenuGroup.NAVIGATION,
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu("robocorp.refreshRobotContentView", MenuGroup.NAVIGATION),
                    ],
                    "view/item/context": [
                        Menu(
                            "robocorp.newFileInRobotContentView",
                            "0_new",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.newFolderInRobotContentView",
                            "0_new",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.renameResourceInRobotContentView",
                            "1_change",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.deleteResourceInRobotContentView",
                            "1_change",
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
                            "robocorp.copyLocatorToClipboard.internal",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.openLocatorTreeSelection",
                            MenuGroup.NAVIGATION,
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.newLocatorUI.tree.internal",
                            MenuGroup.NAVIGATION,
                            "robocorp-code:single-robot-selected",
                        ),
                    ],
                    "view/item/context": [
                        Menu(
                            "robocorp.copyLocatorToClipboard.internal",
                            when="robocorp-code:single-robot-selected",
                        ),
                        Menu(
                            "robocorp.openLocatorTreeSelection",
                            when="robocorp-code:single-robot-selected",
                        ),
                    ],
                },
            ),
            TreeView(
                id="robocorp-cloud-tree",
                name="Robocorp Cloud",
                contextual_title="Robocorp Cloud",
                menus={
                    "view/title": [
                        Menu(ROBOCORP_CLOUD_LOGIN, MenuGroup.NAVIGATION),
                        Menu(ROBOCORP_CLOUD_LOGOUT, MenuGroup.NAVIGATION),
                        Menu("robocorp.refreshCloudView", MenuGroup.NAVIGATION),
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


def get_tree_views():
    ret = {}

    for tree_view_container in TREE_VIEW_CONTAINERS:
        ret[tree_view_container.id] = [
            {"id": tree.id, "name": tree.name, "contextualTitle": tree.contextual_title}
            for tree in tree_view_container.tree_views
        ]
    return ret


def get_activation_events_for_json():
    activation_events = []

    for tree_view_container in TREE_VIEW_CONTAINERS:
        for tree_viewer in tree_view_container.tree_views:
            activation_events.append("onView:" + tree_viewer.id)

    return activation_events


def get_menus():
    menus = {}

    for tree_view_container in TREE_VIEW_CONTAINERS:
        for tree_viewer in tree_view_container.tree_views:
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
