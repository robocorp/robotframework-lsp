import enum
from typing import Optional


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
    NAVIGATION = "navigation"


class Menu:
    def __init__(
        self, command_id, group: Optional[MenuGroup] = None, when: Optional[str] = None
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
                menus=[
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
                    Menu("robocorp.refreshRobotsView", MenuGroup.NAVIGATION),
                ],
            ),
            # TreeView(id="robocorp-tasks-tree", name="Tasks", contextual_title="Tasks"),
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
    menus = []

    for tree_view_container in TREE_VIEW_CONTAINERS:
        for tree_viewer in tree_view_container.tree_views:
            menu: Menu
            for menu in tree_viewer.menus:
                when = f"view == {tree_viewer.id}"
                if menu.when:
                    when += f" && {menu.when}"
                item = {"command": menu.command_id, "when": when}
                if menu.group:
                    item["group"] = menu.group.value
                menus.append(item)

    return menus
