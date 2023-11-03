from typing import Optional

from robocorp_ls_core.command_dispatcher import _SubCommandDispatcher
from robocorp_ls_core.protocols import ActionResult, ActionResultDict, IEndPoint
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code import commands
from robocorp_code.protocols import IRcc

log = get_logger(__name__)

vault_command_dispatcher = _SubCommandDispatcher("_vault")


class _Vault:
    VAULT_WORKSPACE_INFO_CACHE_KEY = "VAULT_WORKSPACE_INFO"

    def __init__(
        self, dir_cache, endpoint: IEndPoint, rcc: IRcc, base_command_dispatcher
    ):
        from robocorp_ls_core.cache import DirCache

        self._dir_cache: DirCache = dir_cache
        self._endpoint = endpoint
        self._rcc = rcc
        base_command_dispatcher.register_sub_command_dispatcher(
            vault_command_dispatcher
        )

    def discard_vault_workspace_info(self):
        self._dir_cache.discard(self.VAULT_WORKSPACE_INFO_CACHE_KEY)

    @vault_command_dispatcher(
        commands.ROBOCORP_UPDATE_LAUNCH_ENV_GET_VAULT_ENV_INTERNAL
    )
    def _update_launch_env_get_vault_env_internal(
        self, params: Optional[dict] = None
    ) -> ActionResultDict:
        action_result: ActionResultDict = self._get_connected_vault_workspace()
        if not action_result["success"]:
            return action_result

        result = action_result["result"]
        if not result:
            return action_result

        workspace_id = result["workspaceId"]

        # Ok, we have the info, let's see if we can get a token.
        authorize_result = self._rcc.cloud_authorize_token(workspace_id)
        if not authorize_result.success:
            return authorize_result.as_dict()

        assert authorize_result.result  # If it's successful, it must be there

        token = authorize_result.result["token"]
        endpoint = authorize_result.result["endpoint"]
        return ActionResult(
            True,
            None,
            {
                "RC_API_SECRET_TOKEN": token,
                "RC_API_SECRET_HOST": endpoint,
                "RC_WORKSPACE_ID": workspace_id,
            },
        ).as_dict()

    @vault_command_dispatcher(commands.ROBOCORP_GET_CONNECTED_VAULT_WORKSPACE_INTERNAL)
    def _get_connected_vault_workspace(
        self, params: Optional[dict] = None
    ) -> ActionResultDict:
        try:
            info = self._dir_cache.load(self.VAULT_WORKSPACE_INFO_CACHE_KEY, dict)
            ret = {
                "workspaceId": info["workspaceId"],
                "organizationName": info["organizationName"],
                "workspaceName": info["workspaceName"],
            }
            return ActionResult(True, "", ret).as_dict()

        except KeyError:
            # It worked (thus, success == True), but it's not available.
            return ActionResult(
                True, "Connected vault workspace not set", None
            ).as_dict()

        except Exception as e:
            log.exception("Error loading WORKSPACE_INFO.")
            return ActionResult(False, str(e), None).as_dict()

    @vault_command_dispatcher(commands.ROBOCORP_SET_CONNECTED_VAULT_WORKSPACE_INTERNAL)
    def _set_connected_vault_workspace(self, params: dict) -> ActionResultDict:
        if "workspaceId" not in params:
            return ActionResult(
                False, "workspaceId not passed in params.", None
            ).as_dict()

        workspace_id = params["workspaceId"]

        if not workspace_id:
            # If set to empty, discard the info.
            self.discard_vault_workspace_info()
            self._endpoint.notify("$/linkedAccountChanged")
            return ActionResult(True, "", None).as_dict()

        if not isinstance(workspace_id, str):
            return ActionResult(
                False, "Expected workspaceId to be a str.", None
            ).as_dict()

        if "organizationName" not in params:
            return ActionResult(
                False, "organizationName not passed in params.", None
            ).as_dict()

        if "workspaceName" not in params:
            return ActionResult(
                False, "workspaceName not passed in params.", None
            ).as_dict()

        organization_name = params["organizationName"]
        if not isinstance(organization_name, str):
            return ActionResult(
                False, "Expected organizationName to be a str.", None
            ).as_dict()

        workspace_name = params["workspaceName"]
        if not isinstance(workspace_name, str):
            return ActionResult(
                False, "Expected workspaceName to be a str.", None
            ).as_dict()

        self._dir_cache.store(
            self.VAULT_WORKSPACE_INFO_CACHE_KEY,
            {
                "workspaceId": workspace_id,
                "organizationName": organization_name,
                "workspaceName": workspace_name,
            },
        )
        self._endpoint.notify("$/linkedAccountChanged")

        return ActionResult(True, "", None).as_dict()
