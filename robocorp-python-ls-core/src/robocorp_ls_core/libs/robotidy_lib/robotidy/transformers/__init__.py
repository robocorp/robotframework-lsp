"""
Transformers are classes used to transform passed Robot Framework code model.

To create your own transformer you need to create file with the same name as your transformer class. Your class
need to inherit from ``ModelTransformer`` or ``ast.NodeTransformer`` class. Finally put name of your transformer in
``TRANSFORMERS`` variable in this file.

If you don't want to run your transformer by default and only when calling robotidy with --transform YourTransformer
then add ``ENABLED = False`` class attribute inside.
"""
from itertools import chain
from robot.utils.importer import Importer
from robot.errors import DataError

from robotidy.utils import RecommendationFinder


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
]


class ImportTransformerError(ValueError):
    pass


def import_transformer(name, args):
    try:
        return Importer().import_class_or_module(name, instantiate_with_args=args)
    except DataError as err:
        if "Creating instance failed" in str(err):
            raise err from None
        short_name = name.split(".")[-1]
        similar_finder = RecommendationFinder()
        similar = similar_finder.find_similar(short_name, TRANSFORMERS)
        raise ImportTransformerError(
            f"Importing transformer '{short_name}' failed. "
            f"Verify if correct name or configuration was provided.{similar}"
        ) from None


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


def load_transformers(allowed_transformers, config, allow_disabled=False, force_order=False):
    """Dynamically load all classes from this file with attribute `name` defined in allowed_transformers"""
    loaded_transformers = []
    allowed_mapped = {name: args for name, args in allowed_transformers} if allowed_transformers else {}
    if not force_order:
        for name in TRANSFORMERS:
            if not allowed_mapped or name in allowed_mapped:
                args = join_configs(allowed_mapped.get(name, ()), config.get(name, ()))
                imported_class = load_transformer(name, args)
                if imported_class is None:
                    continue
                enabled = getattr(imported_class, "ENABLED", True) or args.get("enabled", False)
                if allowed_mapped or allow_disabled or enabled:
                    loaded_transformers.append(imported_class)
    for name in allowed_mapped:
        if force_order or name not in TRANSFORMERS:
            args = join_configs(allowed_mapped.get(name, ()), config.get(name, ()))
            imported_class = load_transformer(name, args)
            if imported_class is not None:
                loaded_transformers.append(imported_class)
    return loaded_transformers
