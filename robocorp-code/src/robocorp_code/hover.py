import datetime
import sys
from typing import Dict, List, Optional, Set

from robocorp_ls_core.lsp import HoverTypedDict, MarkupContent, MarkupKind
from robocorp_ls_core.protocols import IDocument

from robocorp_code.vendored_deps.package_deps._conda_deps import CondaDepInfo
from robocorp_code.vendored_deps.package_deps._deps_protocols import (
    CondaVersionInfo,
    ICondaCloud,
    IPyPiCloud,
    ReleaseData,
)
from robocorp_code.vendored_deps.package_deps._pip_deps import PipDepInfo

# Can be used in tests to force a date.
FORCE_DATETIME_NOW: Optional[datetime.datetime] = None


def hover_on_conda_yaml(
    doc: IDocument,
    line: int,
    col: int,
    pypi_cloud: IPyPiCloud,
    conda_cloud: ICondaCloud,
) -> Optional[HoverTypedDict]:
    from robocorp_ls_core.protocols import IDocumentSelection

    from robocorp_code.vendored_deps.package_deps.analyzer import CondaYamlAnalyzer

    sel: IDocumentSelection = doc.selection(line, col)
    analyzer = CondaYamlAnalyzer(doc.source, doc.path, conda_cloud, pypi_cloud)
    pip_dep = analyzer.find_pip_dep_at(sel.line, sel.col)
    if pip_dep is not None:
        return _hover_handle_pip_dep(pypi_cloud, pip_dep)

    conda_dep: Optional[CondaDepInfo] = analyzer.find_conda_dep_at(sel.line, sel.col)
    if conda_dep is not None:
        return _hover_handle_conda_dep(conda_cloud, conda_dep)
    return None


def hover_on_package_yaml(
    doc: IDocument,
    line: int,
    col: int,
    pypi_cloud: IPyPiCloud,
    conda_cloud: ICondaCloud,
) -> Optional[HoverTypedDict]:
    from robocorp_ls_core.protocols import IDocumentSelection

    from robocorp_code.vendored_deps.package_deps.analyzer import PackageYamlAnalyzer

    sel: IDocumentSelection = doc.selection(line, col)
    analyzer = PackageYamlAnalyzer(doc.source, doc.path, conda_cloud, pypi_cloud)
    pip_dep = analyzer.find_pip_dep_at(sel.line, sel.col)
    if pip_dep is not None:
        return _hover_handle_pip_dep(pypi_cloud, pip_dep)

    conda_dep: Optional[CondaDepInfo] = analyzer.find_conda_dep_at(sel.line, sel.col)
    if conda_dep is not None:
        return _hover_handle_conda_dep(conda_cloud, conda_dep)
    return None


def _create_conda_requirements_desc_parts(
    version_info: CondaVersionInfo,
) -> List[str]:
    """
    Args:
        versions_info: Note that we get multiple versions because conda
        has multiple builds for a single version.
    """
    import msgspec

    from robocorp_code.vendored_deps.package_deps.conda_impl.conda_match_spec import (
        parse_spec_str,
    )

    desc_parts = []
    sub_to_dep_names: Dict[str, Set] = {}

    for (
        subdir,
        build_and_depends,
    ) in version_info.subdir_to_build_and_depends_json_bytes.items():
        for _build, depends in build_and_depends:
            decoded_deps = msgspec.json.decode(depends)
            for dep in decoded_deps:
                dep_info = parse_spec_str(dep)
                try:
                    dep_names = sub_to_dep_names[subdir]
                except KeyError:
                    dep_names = sub_to_dep_names[subdir] = set()
                dep_names.add(dep_info["name"])

    plat = ""
    if sys.platform == "win32":
        plat = "win-64"
    elif sys.platform == "darwin":
        plat = "osx-64"
    elif "linux" in sys.platform:
        plat = "linux-64"

    # Try to use noarch as the basis.
    base_deps = sub_to_dep_names.pop("noarch", None)
    if base_deps:
        base_subdir = "noarch"
        desc_parts.append(f"## Requirements (noarch):")
        desc_parts.extend([f"- {x}" for x in sorted(base_deps)])

    if not base_deps:
        # noarch wasn't there, let's try to use the current platform as
        # the basis.
        base_deps = sub_to_dep_names.pop(plat, None)
        if base_deps:
            base_subdir = plat
            desc_parts.append(f"## Requirements ({plat}):")
            desc_parts.extend([f"- {x}" for x in sorted(base_deps)])

    if not base_deps:
        desc_parts.append("## Requirements not found for the current platform!")
        for sub, plat_deps in sorted(sub_to_dep_names.items()):
            desc_parts.append(f"## Requirements ({sub}):")
            desc_parts.extend([f"- {x}" for x in plat_deps])
    else:
        # Ok, we have a basis, let's show the information for the other platforms
        # as a delta.
        base_as_set = set(base_deps)
        for sub, new_deps in sorted(sub_to_dep_names.items()):
            new_as_set = set(new_deps)

            added_deps = [item for item in new_deps if item not in base_as_set]
            removed_deps = [item for item in base_deps if item not in new_as_set]

            if added_deps or removed_deps:
                desc_parts.append(
                    f"## Requirements difference in {sub} (compared with {base_subdir}):"
                )
                if added_deps:
                    desc_parts.extend([f"- Added: {x}" for x in sorted(added_deps)])
                if removed_deps:
                    desc_parts.extend([f"- Removed: {x}" for x in sorted(removed_deps)])

    return desc_parts


def _hover_handle_conda_dep(
    conda_cloud: ICondaCloud, conda_dep: CondaDepInfo
) -> Optional[HoverTypedDict]:
    from robocorp_code.vendored_deps.package_deps.conda_cloud import (
        sort_conda_versions,
        timestamp_to_datetime,
    )

    if not conda_cloud.is_information_cached():
        return {
            "contents": MarkupContent(
                MarkupKind.Markdown,
                "Hover unavailable (conda-forge information is still not loaded, please retry later).",
            ).to_dict(),
            "range": conda_dep.dep_range,
        }

    sqlite_queries = conda_cloud.sqlite_queries()
    if not sqlite_queries:
        return {
            "contents": MarkupContent(
                MarkupKind.Markdown,
                "Hover unavailable (internal error: sqlite queries not available).",
            ).to_dict(),
            "range": conda_dep.dep_range,
        }

    with sqlite_queries.db_cursors() as db_cursors:
        versions = sqlite_queries.query_versions(conda_dep.name, db_cursors)
        if not versions:
            return {
                "contents": MarkupContent(
                    MarkupKind.Markdown,
                    f"Unable to find {conda_dep.name} in conda-forge.",
                ).to_dict(),
                "range": conda_dep.dep_range,
            }

        current_datetime = (
            FORCE_DATETIME_NOW
            if FORCE_DATETIME_NOW is not None
            else datetime.datetime.now()
        )

        desc_parts = [f"# {conda_dep.name}"]
        last_year = current_datetime - datetime.timedelta(days=365)
        last_year_version_infos: List[CondaVersionInfo] = []
        all_version_infos: List[CondaVersionInfo] = []

        for version in sort_conda_versions(versions):
            version_info = sqlite_queries.query_version_info(
                conda_dep.name, version, db_cursors
            )
            all_version_infos.append(version_info)
            if (
                version_info.timestamp > 0
                and timestamp_to_datetime(version_info.timestamp) > last_year
            ):
                last_year_version_infos.append(version_info)

        desc_parts.append("Conda-forge information:")
        if last_year_version_infos:
            desc_parts.append("\nVersions released in the last 12 months:")
            releases = "`, `".join(x.version for x in reversed(last_year_version_infos))
            desc_parts.append(f"`{releases}`")
        else:
            desc_parts.append("\nNote: no releases in the last 12 months.")

        if all_version_infos:
            last_version_info: Optional[CondaVersionInfo] = all_version_infos[-1]
            if last_version_info:
                desc_parts.append(
                    f"\nLast release version: `{last_version_info.version}` done at: "
                    f"`{format_date(timestamp_to_datetime(last_version_info.timestamp))}`."
                )

                desc_parts.extend(
                    _create_conda_requirements_desc_parts(last_version_info)
                )

    return {
        "contents": MarkupContent(MarkupKind.Markdown, "\n".join(desc_parts)).to_dict(),
        "range": conda_dep.dep_range,
    }


def _hover_handle_pip_dep(
    pypi_cloud: IPyPiCloud, pip_dep: PipDepInfo
) -> HoverTypedDict:
    package_data = pypi_cloud.get_package_data(pip_dep.name)
    if package_data is None:
        return {
            "contents": MarkupContent(
                MarkupKind.Markdown,
                f"Unable to collect pypi information for: {pip_dep.name}",
            ).to_dict(),
            "range": pip_dep.dep_range,
        }
    info = package_data.info
    requires_dist = info["requires_dist"]

    # Note: make it always markdown.
    # description_content_type = info["description_content_type"]
    # if description_content_type == "text/markdown":

    kind = MarkupKind.Markdown

    desc_parts = [f"# {package_data.package_name}"]

    current_datetime = (
        FORCE_DATETIME_NOW
        if FORCE_DATETIME_NOW is not None
        else datetime.datetime.now()
    )
    last_year = current_datetime - datetime.timedelta(days=365)
    releases_data = sorted(package_data.iter_versions_released_after(last_year))

    if pip_dep.constraints:
        for constraint in pip_dep.constraints:
            # Check any constraint ('==', '<', '>'), etc.
            local_version = constraint[1]
            specified_release_data: Optional[
                ReleaseData
            ] = package_data.get_release_data(local_version)
            if specified_release_data is not None:
                desc_parts.append(
                    f"Version `{local_version}` was released at: `{format_date_from_pypi(specified_release_data.upload_time)}`"
                )

    last_release_data: Optional[ReleaseData] = package_data.get_last_release_data()
    if last_release_data:
        desc_parts.append(
            f"\nLast release version: `{last_release_data.version_str}` done at: `{format_date_from_pypi(last_release_data.upload_time)}`."
        )

    if releases_data:
        desc_parts.append("\nVersions released in the last 12 months:")
        releases = "`, `".join(x.version_str for x in reversed(releases_data))
        desc_parts.append(f"`{releases}`")
    else:
        desc_parts.append("\nNote: no releases in the last 12 months.")

    urls_shown = set()
    home_page = package_data.info.get("home_page")
    if home_page:
        urls_shown.add(home_page)
        desc_parts.append(f"\n**Home Page**: {home_page}")

    package_url = package_data.info.get("package_url")
    if package_url:
        if package_url not in urls_shown:
            urls_shown.add(package_url)
            desc_parts.append(f"\n**Package URL**: {package_url}")

    project_urls = package_data.info.get("project_urls")
    if project_urls:
        for url_desc, project_url in project_urls.items():
            if project_url not in urls_shown:
                urls_shown.add(project_url)
                desc_parts.append(f"\n**{url_desc}**: {project_url}")

    if requires_dist:
        desc_parts.append("## Requirements:")
        if isinstance(requires_dist, list):
            desc_parts.extend([f"- {x}" for x in requires_dist])
        else:
            desc_parts.extend(str(requires_dist))
    else:
        desc_parts.append("## (no requirements specified)")

    desc_parts.append("# Description")
    desc_parts.append(info["description"])
    return {
        "contents": MarkupContent(kind, "\n".join(desc_parts)).to_dict(),
        "range": pip_dep.dep_range,
    }


def format_date(d: datetime.datetime) -> str:
    return f"{d.year:02}-{d.month:02}-{d.day:02}"


def format_date_from_pypi(d: Optional[str]) -> str:
    if not d:
        return "<Unknown>"
    try:
        return d.split("T", 1)[0]
    except Exception:
        return d
