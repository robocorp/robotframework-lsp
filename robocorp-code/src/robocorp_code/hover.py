import datetime
from typing import Optional

from robocorp_ls_core.protocols import IDocument

from robocorp_code.deps._deps_protocols import IPyPiCloud, ReleaseData

# Can be used in tests to force a date.
FORCE_DATETIME_NOW: Optional[datetime.datetime] = None


def hover_on_conda_yaml(
    doc: IDocument,
    line: int,
    col: int,
    pypi_cloud: IPyPiCloud,
):

    from robocorp_ls_core.lsp import MarkupContent, MarkupKind
    from robocorp_ls_core.protocols import IDocumentSelection

    from robocorp_code.deps.analyzer import Analyzer

    sel: IDocumentSelection = doc.selection(line, col)
    analyzer = Analyzer(doc.source, doc.path, pypi_cloud)
    pip_dep = analyzer.find_pip_dep_at(sel.line, sel.col)
    if pip_dep is None:
        return None

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
                    f"Version `{local_version}` was released at: `{specified_release_data.upload_time}`"
                )

    if releases_data:
        desc_parts.append("\nVersions released in the last 12 months:")
        releases = "`, `".join(x.version_str for x in releases_data)
        desc_parts.append(f"`{releases}`")
    else:
        last_release_data: Optional[ReleaseData] = package_data.get_last_release_data()
        if last_release_data:
            desc_parts.append(
                f"\nLast release version: `{last_release_data.version_str}` done at: `{last_release_data.upload_time}` (note: no releases in the last 12 months)."
            )
            desc_parts.append(", ".join(x.version_str for x in releases_data))

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
