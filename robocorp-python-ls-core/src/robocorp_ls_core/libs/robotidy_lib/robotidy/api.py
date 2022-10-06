"""
Methods for transforming Robot Framework ast model programmatically.
"""
from typing import Optional

from robotidy.app import Robotidy
from robotidy.cli import TransformType, find_and_read_config, validate_regex
from robotidy.config import Config, FormattingConfig
from robotidy.disablers import RegisterDisablers
from robotidy.files import DEFAULT_EXCLUDES
from robotidy.skip import SkipConfig
from robotidy.utils import ROBOT_VERSION


def get_skip_config(config):
    skip_documentation = config.get("skip_documentation", False)
    skip_return_values = config.get("skip_return_values", False)
    skip_keyword_call = config.get("skip_keyword_call", [])
    skip_keyword_call_pattern = config.get("skip_keyword_call_pattern", [])
    skip_settings = config.get("skip_settings", False)
    skip_arguments = config.get("skip_arguments", False)
    skip_setup = config.get("skip_setup", False)
    skip_teardown = config.get("skip_teardown", False)
    skip_template = config.get("skip_template", False)
    skip_timeout = config.get("skip_timeout", False)
    skip_return = config.get("skip_return", False)
    skip_tags = config.get("skip_tags", False)
    return SkipConfig(
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
    )


def get_formatting_config(config, kwargs):
    space_count = kwargs.get("spacecount", None) or int(config.get("spacecount", 4))
    indent = kwargs.get("indent", None) or int(config.get("indent", space_count))
    cont_indent = kwargs.get("continuation_indent", None) or int(config.get("continuation_indent", space_count))
    formatting_config = FormattingConfig(
        space_count=space_count,
        indent=indent,
        continuation_indent=cont_indent,
        separator=kwargs.get("separator", None) or config.get("separator", "space"),
        line_sep=config.get("lineseparator", "native"),
        start_line=kwargs.get("startline", None) or int(config["startline"]) if "startline" in config else None,
        end_line=kwargs.get("endline", None) or int(config["endline"]) if "endline" in config else None,
        line_length=kwargs.get("line_length", None) or int(config.get("line_length", 120)),
    )
    return formatting_config


def get_robotidy(src: str, output: Optional[str], **kwargs):
    # TODO Refactor - Config should be read in one place both for API and CLI
    # TODO Remove kwargs usage - other SDKs are not using this feature
    config = find_and_read_config((src,))
    config = {k: str(v) if not isinstance(v, (list, dict)) else v for k, v in config.items()}
    converter = TransformType()
    transformers = [converter.convert(tr, None, None) for tr in config.get("transform", ())]
    configurations = [converter.convert(c, None, None) for c in config.get("configure", ())]
    formatting_config = get_formatting_config(config, kwargs)
    exclude = config.get("exclude", None)
    extend_exclude = config.get("extend_exclude", None)
    exclude = validate_regex(exclude if exclude is not None else DEFAULT_EXCLUDES)
    extend_exclude = validate_regex(extend_exclude)
    global_skip = get_skip_config(config)
    configuration = Config(
        transformers=transformers,
        transformers_config=configurations,
        skip=global_skip,
        src=(),
        exclude=exclude,
        extend_exclude=extend_exclude,
        skip_gitignore=False,
        overwrite=False,
        show_diff=False,
        formatting=formatting_config,
        verbose=False,
        check=False,
        output=output,
        force_order=False,
        target_version=ROBOT_VERSION.major,
        color=False,
    )
    return Robotidy(config=configuration)


def transform_model(model, root_dir: str, output: Optional[str] = None, **kwargs) -> Optional[str]:
    """
    :param model: The model to be transformed.
    :param root_dir: Root directory. Configuration file is searched based
    on this directory or one of its parents.
    :param output: Path where transformed model should be saved
    :param kwargs: Default values for global formatting parameters
    such as ``spacecount``, ``startline`` and ``endline``.
    :return: The transformed model converted to string or None if no transformation took place.
    """
    robotidy_class = get_robotidy(root_dir, output, **kwargs)
    disabler_finder = RegisterDisablers(
        robotidy_class.config.formatting.start_line, robotidy_class.config.formatting.end_line
    )
    disabler_finder.visit(model)
    if disabler_finder.file_disabled:
        return None
    diff, _, new_model = robotidy_class.transform(model, disabler_finder.disablers)
    if not diff:
        return None
    return new_model.text
