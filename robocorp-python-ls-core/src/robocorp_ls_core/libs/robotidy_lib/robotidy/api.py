"""
Methods for transforming Robot Framework ast model programmatically.
"""
from typing import Optional

from robotidy.app import Robotidy
from robotidy.cli import find_and_read_config, TransformType, validate_regex
from robotidy.files import DEFAULT_EXCLUDES
from robotidy.utils import GlobalFormattingConfig


class RobotidyAPI(Robotidy):
    def __init__(self, src: str, output: Optional[str], **kwargs):
        config = find_and_read_config((src,))
        config = {k: str(v) if not isinstance(v, (list, dict)) else v for k, v in config.items()}
        converter = TransformType()
        transformers = [converter.convert(tr, None, None) for tr in config.get("transform", ())]
        configurations = [converter.convert(c, None, None) for c in config.get("configure", ())]
        formatting_config = GlobalFormattingConfig(
            space_count=kwargs.get("spacecount", None) or int(config.get("spacecount", 4)),
            separator=kwargs.get("separator", None) or config.get("separator", "space"),
            line_sep=config.get("lineseparator", "native"),
            start_line=kwargs.get("startline", None) or int(config["startline"]) if "startline" in config else None,
            end_line=kwargs.get("endline", None) or int(config["endline"]) if "endline" in config else None,
        )
        exclude = config.get("exclude", None)
        extend_exclude = config.get("extend_exclude", None)
        exclude = validate_regex(exclude if exclude is not None else DEFAULT_EXCLUDES)
        extend_exclude = validate_regex(extend_exclude)
        super().__init__(
            transformers=transformers,
            transformers_config=configurations,
            src=(),
            exclude=exclude,
            extend_exclude=extend_exclude,
            overwrite=False,
            show_diff=False,
            formatting_config=formatting_config,
            verbose=False,
            check=False,
            output=output,
            force_order=False,
        )


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
    transformer = RobotidyAPI(root_dir, output, **kwargs)
    diff, _, new_model = transformer.transform(model)
    if not diff:
        return None
    return new_model.text
