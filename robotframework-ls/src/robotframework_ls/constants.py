from robocorp_ls_core.constants import *
from string import Template


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
