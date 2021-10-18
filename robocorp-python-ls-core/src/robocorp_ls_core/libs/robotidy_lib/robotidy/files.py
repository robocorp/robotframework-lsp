from typing import Iterable, Dict, Any, List, Iterator, Tuple, Pattern, Optional
from pathlib import Path
import toml
from functools import lru_cache

import click
from pathspec import PathSpec


DEFAULT_EXCLUDES = r"/(\.direnv|\.eggs|\.git|\.hg|\.nox|\.tox|\.venv|venv|\.svn)/"
INCLUDE_EXT = (".robot", ".resource")


@lru_cache()
def find_project_root(srcs: Iterable[str]) -> Path:
    """Return a directory containing .git, or robotidy.toml.
    That directory will be a common parent of all files and directories
    passed in `srcs`.
    If no directory in the tree contains a marker that would specify it's the
    project root, the root of the file system is returned.
    """
    if not srcs:
        return Path("/").resolve()

    path_srcs = [Path(Path.cwd(), src).resolve() for src in srcs]

    # A list of lists of parents for each 'src'. 'src' is included as a
    # "parent" of itself if it is a directory
    src_parents = [list(path.parents) + ([path] if path.is_dir() else []) for path in path_srcs]

    common_base = max(
        set.intersection(*(set(parents) for parents in src_parents)),
        key=lambda path: path.parts,
    )

    for directory in (common_base, *common_base.parents):
        if (directory / ".git").exists():
            return directory

        if (directory / "robotidy.toml").is_file():
            return directory

        if (directory / "pyproject.toml").is_file():
            return directory

    return directory


def find_and_read_config(src_paths: Iterable[str]) -> Dict[str, Any]:
    project_root = find_project_root(src_paths)
    config_path = project_root / "robotidy.toml"
    if config_path.is_file():
        return read_pyproject_config(str(config_path))
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.is_file():
        return read_pyproject_config(str(pyproject_path))
    return {}


def load_toml_file(path: str) -> Dict[str, Any]:
    try:
        config = toml.load(path)
        return config
    except (toml.TomlDecodeError, OSError) as e:
        raise click.FileError(filename=path, hint=f"Error reading configuration file: {e}")


def read_pyproject_config(path: str) -> Dict[str, Any]:
    config = load_toml_file(path)
    config = config.get("tool", {}).get("robotidy", {})
    if config:
        click.echo(f"Loaded configuration from {path}")
    return {k.replace("--", "").replace("-", "_"): v for k, v in config.items()}


@lru_cache()
def get_gitignore(root: Path) -> PathSpec:
    """Return a PathSpec matching gitignore content if present."""
    gitignore = root / ".gitignore"
    lines: List[str] = []
    if gitignore.is_file():
        with gitignore.open(encoding="utf-8") as gf:
            lines = gf.readlines()
    return PathSpec.from_lines("gitwildmatch", lines)


def path_is_excluded(
    normalized_path: str,
    pattern: Optional[Pattern[str]],
) -> bool:
    match = pattern.search(normalized_path) if pattern else None
    return bool(match and match.group(0))


def get_paths(src: Tuple[str, ...], exclude: Optional[Pattern], extend_exclude: Optional[Pattern]):
    root = find_project_root(src)
    gitignore = get_gitignore(root)
    sources = set()
    for s in src:
        if s == "-":
            sources.add("-")
            continue
        path = Path(s).resolve()
        if path.is_file():
            sources.add(path)
        elif path.is_dir():
            sources.update(iterate_dir((path,), exclude, extend_exclude, gitignore))
        elif s == "-":
            sources.add(path)

    return sources


def iterate_dir(
    paths: Iterable[Path],
    exclude: Optional[Pattern],
    extend_exclude: Optional[Pattern],
    gitignore: Optional[PathSpec],
) -> Iterator[Path]:
    for path in paths:
        if gitignore is not None and gitignore.match_file(path):
            continue
        if path_is_excluded(str(path), exclude) or path_is_excluded(str(path), extend_exclude):
            continue
        if path.is_dir() and exclude and not exclude.match(path.name):
            yield from iterate_dir(
                path.iterdir(),
                exclude,
                extend_exclude,
                gitignore + get_gitignore(path) if gitignore is not None else None,
            )
        elif path.is_file():
            if path.suffix not in INCLUDE_EXT:
                continue
            yield path
