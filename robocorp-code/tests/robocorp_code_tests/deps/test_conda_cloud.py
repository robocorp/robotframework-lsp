import os
import threading
from dataclasses import asdict
from pathlib import Path


def test_conda_cloud_index(datadir, data_regression):
    from robocorp_code.deps.conda_cloud import SqliteQueries, index_conda_info

    target_sqlite = datadir / "sqlite.db"
    index_conda_info(datadir / "noarch-testdata.json", target_sqlite)
    sqlite_helper = SqliteQueries(target_sqlite)
    names = sqlite_helper.query_names()
    assert len(names) == 292

    # This one has 0.1.5 with multiple build ids.
    versions = sqlite_helper.query_versions("arn")
    assert versions == {"0.1.5"}

    versions = sqlite_helper.query_versions("aadict")
    assert versions == {"0.2.3", "0.2.5"}

    with sqlite_helper.db_cursors() as db_cursors:
        name = "aadict"
        # We can also reuse the cursor (it's a bit faster when doing multiple queries).
        versions = sqlite_helper.query_versions(name, db_cursors=db_cursors)
        assert versions == {"0.2.3", "0.2.5"}
        infos = []
        for version in sorted(versions):
            version_info = sqlite_helper.query_version_info(
                name, version, db_cursors=db_cursors
            )
            dct = asdict(version_info)

            # Convert the bytes from for the depends to a str.
            new_subdir_to_build_and_depends = {}
            for subdir, build_and_depends in list(
                dct["subdir_to_build_and_depends_json_bytes"].items()
            ):
                new_lst = sorted(
                    [(x[0], x[1].decode("utf-8")) for x in build_and_depends]
                )
                new_subdir_to_build_and_depends[subdir] = new_lst
            dct[
                "subdir_to_build_and_depends_json_bytes"
            ] = new_subdir_to_build_and_depends
            infos.append(dct)

        data_regression.check(infos)
    os.remove(target_sqlite)


def _test_check_manual():
    # Manual performance tests with a downloaded file.
    from robocorp_code.deps.conda_cloud import SqliteQueries, index_conda_info

    p = Path(r"C:\temp\conda_check\linux-64.db")
    import os

    if p.exists():
        os.remove(p)

    index_conda_info(Path(r"C:\temp\conda_check\linux-64.json"), p)
    sqlite_queries = SqliteQueries(p)
    with sqlite_queries.db_cursors() as db_cursors:
        names = sqlite_queries.query_names(db_cursors=db_cursors)
        print(len(names))
        name = "numpy"
        # for name in sorted(names)[:100]:
        versions = sqlite_queries.query_versions(name, db_cursors=db_cursors)
        print("---")
        for version in versions:
            print(name, version)
            version_info = sqlite_queries.query_version_info(
                name, version, db_cursors=db_cursors
            )
            print(version_info)


def test_conda_cloud(datadir):
    from robocorp_ls_core.basic import wait_for_condition

    from robocorp_code.deps.conda_cloud import CondaCloud, State

    cache_dir = datadir / "cache"
    conda_cloud = CondaCloud(cache_dir, reindex_if_old=True)
    assert not conda_cloud.is_information_cached()

    original_download = conda_cloud._download

    def create_mock_download():
        # Just download once. Get from cache afterwards.
        download_cache: dict = {}

        def mock_download(url: str, target_json: Path, arch: str):
            try:
                contents = download_cache[url]
            except KeyError:
                target_json, arch = original_download(url, target_json, arch)

                # Save in the cache.
                with target_json.open("rb") as stream:
                    download_cache[url] = stream.read()

            else:
                # Write cache contents to file.
                with target_json.open("wb") as stream:
                    stream.write(contents)

            return target_json, arch

        return mock_download

    conda_cloud._download = create_mock_download()

    event = threading.Event()

    def on_finished(*args, **kwargs):
        event.set()

    conda_cloud.schedule_update(on_finished, wait=True)
    assert event.wait(10)

    assert conda_cloud.is_information_cached()

    sqlite_queries = conda_cloud.sqlite_queries()
    assert sqlite_queries
    with sqlite_queries.db_cursors() as db_cursors:
        names = sqlite_queries.query_names(db_cursors=db_cursors)
        assert len(names) > 1000
        found_deps = False
        for name in sorted(names)[:50]:
            versions = sqlite_queries.query_versions(name, db_cursors=db_cursors)
            assert len(versions) >= 1
            for version in versions:
                version_info = sqlite_queries.query_version_info(
                    name, version, db_cursors=db_cursors
                )
                assert len(version_info.subdir_to_build_and_depends_json_bytes) >= 1
                found_deps = (
                    found_deps
                    or len(version_info.subdir_to_build_and_depends_json_bytes) >= 1
                )
    # i.e.: at least one of the 50 packages we've queried must have
    # dependencies/subdir.
    assert found_deps

    location1 = conda_cloud._load_latest_index_dir_location()
    assert conda_cloud._state == State.done
    assert location1
    assert location1.name.endswith("index_0001")

    conda_cloud.schedule_update(wait=True, force=True)
    location2 = conda_cloud._load_latest_index_dir_location()
    assert location2
    assert location2.name.endswith("index_0002")

    conda_cloud.schedule_update(wait=True, force=True)
    assert conda_cloud._state == State.done
    location3 = conda_cloud._load_latest_index_dir_location()
    assert location3
    assert location3.name.endswith("index_0003")

    # We always keep 1 as buffer and remove the previous ones.
    wait_for_condition(lambda: not location1.exists())
    assert location2.exists()

    # Ok, now, let's see that creating a new one does say that it
    # was downloaded already.
    conda_cloud = CondaCloud(cache_dir, reindex_if_old=True)
    assert conda_cloud._state == State.done
