import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple, Union
from robotidy import skip


CLI_OPTIONS_LIST = [
    {
        "name": "Run only selected transformers",
        "options": ["--transform"],
    },
    {
        "name": "Work modes",
        "options": ["--overwrite", "--diff", "--check", "--force-order"],
    },
    {
        "name": "Documentation",
        "options": ["--list", "--desc"],
    },
    {
        "name": "Configuration",
        "options": ["--configure", "--config"],
    },
    {
        "name": "Global formatting settings",
        "options": [
            "--spacecount",
            "--indent",
            "--continuation-indent",
            "--line-length",
            "--lineseparator",
            "--separator",
            "--startline",
            "--endline",
        ],
    },
    {
        "name": "File exclusion",
        "options": ["--exclude", "--extend-exclude", "--skip-gitignore"],
    },
    skip.option_group,
    {
        "name": "Other",
        "options": [
            "--target-version",
            "--verbose",
            "--color",
            "--output",
            "--version",
            "--help",
        ],
    },
]

try:
    import rich_click as click

    click.rich_click.USE_RICH_MARKUP = True
    click.rich_click.USE_MARKDOWN = True
    click.rich_click.STYLE_OPTION = "bold sky_blue3"
    click.rich_click.STYLE_SWITCH = "bold sky_blue3"
    click.rich_click.STYLE_METAVAR = "bold white"
    click.rich_click.STYLE_OPTION_DEFAULT = "grey37"
    click.rich_click.STYLE_OPTIONS_PANEL_BORDER = "grey66"
    click.rich_click.STYLE_USAGE = "magenta"
    click.rich_click.OPTION_GROUPS = {
        "robotidy": CLI_OPTIONS_LIST,
        "python -m robotidy": CLI_OPTIONS_LIST,
    }

except ImportError:
    import click

from robotidy.app import Robotidy
from robotidy.config import Config, FormattingConfig
from robotidy.decorators import catch_exceptions
from robotidy.files import DEFAULT_EXCLUDES, find_and_read_config, read_pyproject_config

try:
    from robotidy.rich_console import console
except:

    class console:
        def print(self, *args, **kwargs):
            print(*args, **kwargs)

    console = console()
from robotidy.transformers import load_transformers
from robotidy.utils import (
    ROBOT_VERSION,
    RecommendationFinder,
    TargetVersion,
    split_args_from_name_or_path,
)
from robotidy.version import __version__


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


class TransformType(click.ParamType):
    name = "transform"

    def convert(self, value, param, ctx):
        name, args = split_args_from_name_or_path(value.replace(" ", ""))
        return name, args


def parse_opt(opt):
    while opt and opt[0] == "-":
        opt = opt[1:]
    return opt.replace("-", "_")


def validate_config_options(params, config):
    if params is None:
        return
    allowed = {parse_opt(opt) for param in params for opt in param.opts}
    for conf in config:
        if conf not in allowed:
            rec_finder = RecommendationFinder()
            similar = rec_finder.find(conf, list(allowed))
            raise click.NoSuchOption(conf, possibilities=similar)


def read_config(
    ctx: click.Context, param: click.Parameter, value: Optional[str]
) -> Optional[str]:
    # if --config was not used, try to find pyproject.toml or robotidy.toml file
    if value:
        config = read_pyproject_config(value)
    else:
        config = find_and_read_config(ctx.params["src"] or (str(Path(".").resolve()),))
    if not config:
        return
    # Sanitize the values to be Click friendly. For more information please see:
    # https://github.com/psf/black/issues/1458
    # https://github.com/pallets/click/issues/1567
    config = {
        k: str(v) if not isinstance(v, (list, dict)) else v for k, v in config.items()
    }
    if "src" in config:
        config["src"] = tuple(config["src"])
    validate_config_options(ctx.command.params, config)
    default_map: Dict[str, Any] = {}
    if ctx.default_map:
        default_map.update(ctx.default_map)
    default_map.update(config)
    ctx.default_map = default_map


def validate_regex_callback(
    ctx: click.Context,
    param: click.Parameter,
    value: Optional[str],
) -> Optional[Pattern]:
    return validate_regex(value)


def validate_target_version(
    ctx: click.Context,
    param: Union[click.Option, click.Parameter],
    value: Optional[str],
) -> Optional[int]:
    if value is None:
        return ROBOT_VERSION.major
    version = TargetVersion[value.upper()].value
    if version > ROBOT_VERSION.major:
        raise click.BadParameter(
            f"Target Robot Framework version ({version}) should not be higher than installed version ({ROBOT_VERSION})."
        )
    return version


def validate_regex(value: Optional[str]) -> Optional[Pattern]:
    try:
        return re.compile(value) if value is not None else None
    except re.error:
        raise click.BadParameter("Not a valid regular expression")


def print_transformer_docs(transformer):
    from rich.markdown import Markdown

    md = Markdown(
        str(transformer), code_theme="native", inline_code_lexer="robotframework"
    )
    console.print(md)


def print_description(name: str, target_version: int):
    transformers = load_transformers(
        None, {}, allow_disabled=True, target_version=target_version
    )
    transformer_by_names = {
        transformer.name: transformer for transformer in transformers
    }
    if name == "all":
        for transformer in transformers:
            print_transformer_docs(transformer)
    elif name in transformer_by_names:
        print_transformer_docs(transformer_by_names[name])
    else:
        rec_finder = RecommendationFinder()
        similar = rec_finder.find_similar(name, transformer_by_names.keys())
        click.echo(f"Transformer with the name '{name}' does not exist.{similar}")
        return 1
    return 0


def print_transformers_list(target_version: int):
    from rich.table import Table

    table = Table(title="Transformers", header_style="bold red")
    table.add_column("Name", justify="left", no_wrap=True)
    table.add_column("Enabled by default")
    transformers = load_transformers(
        None, {}, allow_disabled=True, target_version=target_version
    )
    for transformer in transformers:
        decorated_enable = (
            "Yes" if transformer.enabled_by_default else "[bold magenta]No"
        )
        table.add_row(transformer.name, decorated_enable)
    console.print(table)
    console.print("Transformers are listed in the order they are run by default.")
    console.print(
        "To see detailed docs run:\n"
        "    [bold]robotidy --desc [bold magenta]transformer_name[/][/]\n"
        "or\n"
        "    [bold]robotidy --desc [bold blue]all[/][/]\n\n"
        "Non-default transformers needs to be selected explicitly with [bold cyan]--transform[/] or "
        "configured with param `enabled=True`.\n"
    )


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--transform",
    "-t",
    type=TransformType(),
    multiple=True,
    metavar="TRANSFORMER_NAME",
    help="Transform files from \[PATH(S)] with given transformer",
)
@click.option(
    "--configure",
    "-c",
    type=TransformType(),
    multiple=True,
    metavar="TRANSFORMER_NAME:PARAM=VALUE",
    help="Configure transformers",
)
@click.argument(
    "src",
    nargs=-1,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, allow_dash=True
    ),
    is_eager=True,
    metavar="[PATH(S)]",
)
@click.option(
    "--exclude",
    type=str,
    callback=validate_regex_callback,
    help=(
        "A regular expression that matches files and directories that should be"
        " excluded on recursive searches. An empty value means no paths are excluded."
        " Use forward slashes for directories on all platforms."
    ),
    show_default=f"{DEFAULT_EXCLUDES}",
)
@click.option(
    "--extend-exclude",
    type=str,
    callback=validate_regex_callback,
    help=(
        "Like **--exclude**, but adds additional files and directories on top of the"
        " excluded ones. (Useful if you simply want to add to the default)"
    ),
)
@click.option(
    "--skip-gitignore",
    is_flag=True,
    show_default=True,
    help="Skip **.gitignore** files and do not ignore files listed inside.",
)
@click.option(
    "--config",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        allow_dash=False,
        path_type=str,
    ),
    is_eager=True,
    callback=read_config,
    help="Read configuration from FILE path.",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=None,
    help="Write changes back to file",
    show_default=True,
)
@click.option(
    "--diff",
    is_flag=True,
    help="Output diff of each processed file.",
    show_default=True,
)
@click.option(
    "--color/--no-color",
    default=True,
    help="Enable ANSI coloring the output",
    show_default=True,
)
@click.option(
    "--check",
    is_flag=True,
    help="Don't overwrite files and just return status. Return code 0 means nothing would change. "
    "Return code 1 means that at least 1 file would change. Any internal error will overwrite this status.",
    show_default=True,
)
@click.option(
    "-s",
    "--spacecount",
    type=click.types.INT,
    default=4,
    help="The number of spaces between cells",
    show_default=True,
)
@click.option(
    "--indent",
    type=click.types.INT,
    default=None,
    help="The number of spaces to be used as indentation",
    show_default="same as --spacecount value",
)
@click.option(
    "--continuation-indent",
    type=click.types.INT,
    default=None,
    help="The number of spaces to be used as separator after ... (line continuation) token",
    show_default="same as --spacecount value]",
)
@click.option(
    "-ls",
    "--lineseparator",
    type=click.types.Choice(["native", "windows", "unix", "auto"]),
    default="native",
    help="""
    Line separator to use in the outputs:
    - **native**:  use operating system's native line endings
    - windows: use Windows line endings (CRLF)
    - unix:    use Unix line endings (LF)
    - auto:    maintain existing line endings (uses what's used in the first line)
    """,
    show_default=True,
)
@click.option(
    "--separator",
    type=click.types.Choice(["space", "tab"]),
    default="space",
    help="""
    Token separator to use in the outputs:
    - **space**:   use --spacecount spaces to separate tokens
    - tab:     use a single tabulation to separate tokens
    """,
    show_default=True,
)
@click.option(
    "-sl",
    "--startline",
    default=None,
    type=int,
    help="Limit robotidy only to selected area. If **--endline** is not provided, format text only at **--startline**. "
    "Line numbers start from 1.",
)
@click.option(
    "-el",
    "--endline",
    default=None,
    type=int,
    help="Limit robotidy only to selected area. Line numbers start from 1.",
)
@click.option(
    "--line-length",
    default=120,
    type=int,
    help="Max allowed characters per line",
    show_default=True,
)
@click.option(
    "--list",
    "-l",
    is_eager=True,
    is_flag=True,
    help="List available transformers and exit.",
)
@click.option(
    "--desc",
    "-d",
    default=None,
    metavar="TRANSFORMER_NAME",
    help="Show documentation for selected transformer.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False, writable=True, allow_dash=False),
    default=None,
    metavar="PATH",
    help="Use this option to override file destination path.",
)
@click.option(
    "-v", "--verbose", is_flag=True, help="More verbose output", show_default=True
)
@click.option(
    "--force-order",
    is_flag=True,
    help="Transform files using transformers in order provided in cli",
)
@click.option(
    "--target-version",
    "-tv",
    type=click.Choice([v.name.lower() for v in TargetVersion], case_sensitive=False),
    callback=validate_target_version,
    help="Only enable transformers supported in set target version",
    show_default="installed Robot Framework version",
)
@skip.documentation_option
@skip.return_values_option
@skip.keyword_call_option
@skip.keyword_call_pattern_option
@skip.settings_option
@skip.arguments_option
@skip.setup_option
@skip.teardown_option
@skip.timeout_option
@skip.template_option
@skip.return_option
@skip.tags_option
@skip.block_comments_option
@click.version_option(version=__version__, prog_name="robotidy")
@click.pass_context
@catch_exceptions
def cli(
    ctx: click.Context,
    transform: List[Tuple[str, List]],
    configure: List[Tuple[str, List]],
    src: Tuple[str, ...],
    exclude: Optional[Pattern],
    extend_exclude: Optional[Pattern],
    skip_gitignore: bool,
    overwrite: bool,
    diff: bool,
    color: bool,
    check: bool,
    spacecount: int,
    indent: Optional[int],
    continuation_indent: Optional[int],
    lineseparator: str,
    verbose: bool,
    config: Optional[str],
    separator: Optional[str],
    startline: Optional[int],
    endline: Optional[int],
    line_length: int,
    list: bool,
    desc: Optional[str],
    output: Optional[Path],
    force_order: bool,
    target_version: int,
    skip_documentation: bool,
    skip_return_values: bool,
    skip_keyword_call: List[str],
    skip_keyword_call_pattern: List[str],
    skip_settings: bool,
    skip_arguments: bool,
    skip_setup: bool,
    skip_teardown: bool,
    skip_timeout: bool,
    skip_template: bool,
    skip_return: bool,
    skip_tags: bool,
    skip_block_comments: bool,
):
    """
    Robotidy is a tool for formatting Robot Framework source code.
    Full documentation available at <https://robotidy.readthedocs.io> .
    """
    if list:
        print_transformers_list(target_version)
        sys.exit(0)
    if desc is not None:
        return_code = print_description(desc, target_version)
        sys.exit(return_code)
    if not src:
        if ctx.default_map is not None:
            src = ctx.default_map.get("src", None)
        if not src:
            print(
                "No source path provided. Run robotidy --help to see how to use robotidy"
            )
            sys.exit(1)

    if exclude is None:
        exclude = re.compile(DEFAULT_EXCLUDES)

    if config and verbose:
        click.echo(f"Loaded {config} configuration file")

    if overwrite is None:
        # None is default, with check not set -> overwrite, with check set -> overwrite only when overwrite flag is set
        overwrite = not check

    if color:
        color = "NO_COLOR" not in os.environ

    skip_config = skip.SkipConfig(
        documentation=skip_documentation,
        return_values=skip_return_values,
        keyword_call=skip_keyword_call,
        keyword_call_pattern=skip_keyword_call_pattern,
        settings=skip_settings,
        arguments=skip_arguments,
        setup=skip_setup,
        teardown=skip_teardown,
        template=skip_template,
        timeout=skip_timeout,
        return_statement=skip_return,
        tags=skip_tags,
        block_comments=skip_block_comments,
    )

    formatting = FormattingConfig(
        space_count=spacecount,
        indent=indent,
        continuation_indent=continuation_indent,
        line_sep=lineseparator,
        start_line=startline,
        separator=separator,
        end_line=endline,
        line_length=line_length,
    )
    config = Config(
        formatting=formatting,
        skip=skip_config,
        transformers=transform,
        transformers_config=configure,
        src=src,
        exclude=exclude,
        extend_exclude=extend_exclude,
        skip_gitignore=skip_gitignore,
        overwrite=overwrite,
        show_diff=diff,
        verbose=verbose,
        check=check,
        output=output,
        force_order=force_order,
        target_version=target_version,
        color=color,
    )
    tidy = Robotidy(config=config)
    status = tidy.transform_files()
    sys.exit(status)
