"""
Transformers are classes used to transform passed Robot Framework code model.

To create your own transformer you need to create file with the same name as your transformer class. Your class
need to inherit from ``ModelTransformer`` or ``ast.NodeTransformer`` class. Finally put name of your transformer in
``TRANSFORMERS`` variable in this file.

If you don't want to run your transformer by default and only when calling robotidy with --transform YourTransformer
then add ``ENABLED = False`` class attribute inside.
"""
from itertools import chain

import click
from robot.errors import DataError
from robot.utils.importer import Importer

from robotidy.exceptions import ImportTransformerError, InvalidParameterError, InvalidParameterFormatError
from robotidy.utils import ROBOT_VERSION, RecommendationFinder

TRANSFORMERS = [
    "AddMissingEnd",
    "NormalizeSeparators",
    "DiscardEmptySections",
    "MergeAndOrderSections",
    "RemoveEmptySettings",
    "NormalizeAssignments",
    "OrderSettings",
    "OrderSettingsSection",
    "NormalizeTags",
    "OrderTags",
    "AlignSettingsSection",
    "AlignVariablesSection",
    "AlignTestCases",
    "NormalizeNewLines",
    "NormalizeSectionHeaderName",
    "NormalizeSettingName",
    "ReplaceRunKeywordIf",
    "SplitTooLongLine",
    "SmartSortKeywords",
    "RenameTestCases",
    "RenameKeywords",
    "ReplaceReturns",
    "ReplaceBreakContinue",
    "InlineIf",
]


IMPORTER = Importer()


def import_transformer(name, args):
    short_name = name.split(".")[-1]
    try:
        imported_class = IMPORTER.import_class_or_module(name)
        spec = IMPORTER._get_arg_spec(imported_class)
        positional, named = resolve_args(short_name, spec, args)
    except DataError:
        similar_finder = RecommendationFinder()
        similar = similar_finder.find_similar(short_name, TRANSFORMERS)
        raise ImportTransformerError(
            f"Importing transformer '{short_name}' failed. "
            f"Verify if correct name or configuration was provided.{similar}"
        ) from None
    return imported_class(*positional, **dict(named))


def resolve_args(transformer, spec, args):
    if args and not spec.argument_names:
        raise InvalidParameterError(transformer, " This transformer does not accept arguments but they were provided.")
    arg_names = [arg.split("=")[0] for arg in args]
    for arg in arg_names:
        # it's fine to only check for first non-matching parameter
        if arg not in spec.argument_names:
            similar_finder = RecommendationFinder()
            similar = similar_finder.find_similar(arg, spec.argument_names)
            if not similar:
                arg_names = "\n".join(spec.argument_names)
                similar = f" This transformer accepts following arguments: {arg_names}"
            raise InvalidParameterError(transformer, similar) from None
    try:
        return spec.resolve(args)
    except ValueError as err:
        raise InvalidParameterError(transformer, f" {err}") from None


def load_transformer(name, args):
    if not args.get("enabled", True):
        return None
    args = [f"{key}={value}" for key, value in args.items() if key != "enabled"]
    import_name = f"robotidy.transformers.{name}" if name in TRANSFORMERS else name
    return import_transformer(import_name, args)


def join_configs(args, config):
    # args are from --transform Name:param=value and config is from --configure
    temp_args = {}
    for arg in chain(args, config):
        param, value = arg.split("=", maxsplit=1)
        if param == "enabled":
            temp_args[param] = value.lower() == "true"
        else:
            temp_args[param] = value
    return temp_args


def get_args(transformer, allowed_mapped, config):
    try:
        return join_configs(allowed_mapped.get(transformer, ()), config.get(transformer, ()))
    except ValueError:
        raise InvalidParameterFormatError(transformer) from None


def validate_config(config, allowed_mapped):
    for transformer in config:
        if transformer in allowed_mapped or transformer in TRANSFORMERS:
            continue
        similar_finder = RecommendationFinder()
        similar = similar_finder.find_similar(transformer, TRANSFORMERS + list(allowed_mapped.keys()))
        raise ImportTransformerError(
            f"Configuring transformer '{transformer}' failed. " f"Verify if correct name was provided.{similar}"
        ) from None


def can_run_in_robot_version(transformer, overwritten, target_version):
    if not hasattr(transformer, "MIN_VERSION"):
        return True
    if target_version >= transformer.MIN_VERSION:
        return True
    if overwritten:
        # --transform TransformerDisabledInVersion or --configure TransformerDisabledInVersion:enabled=True
        if target_version == ROBOT_VERSION.major:
            click.echo(
                f"{transformer.__class__.__name__} transformer requires Robot Framework {transformer.MIN_VERSION}.* "
                f"version but you have {ROBOT_VERSION} installed. "
                f"Upgrade installed Robot Framework if you want to use this transformer."
            )
        else:
            click.echo(
                f"{transformer.__class__.__name__} transformer requires Robot Framework {transformer.MIN_VERSION}.* "
                f"version but you set --target-version rf{target_version}. "
                f"Set --target-version to rf{transformer.MIN_VERSION} or do not forcefully enable this transformer "
                f"with --transform / enable parameter."
            )
    return False


def load_transformers(allowed_transformers, config, target_version, allow_disabled=False, force_order=False):
    """Dynamically load all classes from this file with attribute `name` defined in allowed_transformers"""
    loaded_transformers = []
    allowed_mapped = {name: args for name, args in allowed_transformers} if allowed_transformers else {}
    validate_config(config, allowed_mapped)
    if not force_order:
        for name in TRANSFORMERS:
            if not allowed_mapped or name in allowed_mapped:
                args = get_args(name, allowed_mapped, config)
                imported_class = load_transformer(name, args)
                if imported_class is None:
                    continue
                enabled = getattr(imported_class, "ENABLED", True) or args.get("enabled", False)
                if allowed_mapped or allow_disabled or enabled:
                    overwritten = name in allowed_mapped or args.get("enabled", False)
                    if can_run_in_robot_version(imported_class, overwritten=overwritten, target_version=target_version):
                        loaded_transformers.append(imported_class)
                    elif allow_disabled:
                        setattr(imported_class, "ENABLED", False)
                        loaded_transformers.append(imported_class)
    for name in allowed_mapped:
        if force_order or name not in TRANSFORMERS:
            args = get_args(name, allowed_mapped, config)
            imported_class = load_transformer(name, args)
            if imported_class is not None:
                if can_run_in_robot_version(imported_class, overwritten=True, target_version=target_version):
                    loaded_transformers.append(imported_class)
    return loaded_transformers
