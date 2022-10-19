from robocorp_ls_core.constants import *
from robocorp_ls_core.options import USE_TIMEOUTS
from typing import Optional
from string import Template

DEFAULT_COMPLETIONS_TIMEOUT: int = 8
DEFAULT_COLLECT_DOCS_TIMEOUT: int = 40
DEFAULT_LIST_TESTS_TIMEOUT: int = 20
if not USE_TIMEOUTS:
    # A whole month of timeout seems good enough as a max.
    DEFAULT_COMPLETIONS_TIMEOUT = 60 * 60 * 24 * 30
    DEFAULT_COLLECT_DOCS_TIMEOUT = DEFAULT_COMPLETIONS_TIMEOUT
    DEFAULT_LIST_TESTS_TIMEOUT = DEFAULT_COMPLETIONS_TIMEOUT

# Robot Flow Explorer template used as wrapper for the React Application
# Substitute the $rfe_options & $rfe_data to render properly
DEFAULT_ROBOT_FLOW_EXPLORER_HTML_TEMPLATE: Template = Template(
    """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
    <title>Robot Flow Explorer</title>
    <link rel="icon" href="$rfe_favicon_path" />
    <script id="options" type="application/json">
      $rfe_options
    </script>
    <script id="data" type="application/json">
      $rfe_data
    </script>
  </head>
  <body>
    <noscript>Robot Visualization requires JavaScript</noscript>
    <div id="root"></div>
    <script defer="defer" src="$rfe_js_path"></script>
  </body>
</html>
"""
)

DEFAULT_ROBOT_FLOW_EXPLORER_OPTIONS: dict = {"theme": "light", "showCopyright": True}
