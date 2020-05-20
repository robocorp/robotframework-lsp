# Original work Copyright 2017 Palantir Technologies, Inc. (MIT)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest
from robocode_ls_core.constants import IS_WIN
from robocode_ls_core import uris

unix_only = pytest.mark.skipif(IS_WIN, reason="Unix only")
windows_only = pytest.mark.skipif(not IS_WIN, reason="Windows only")


@unix_only
@pytest.mark.parametrize(
    "uri,path",
    [
        ("file:///foo/bar#frag", "/foo/bar"),
        ("file:/foo/bar#frag", "/foo/bar"),
        ("file:/foo/space%20%3Fbar#frag", "/foo/space ?bar"),
    ],
)
def test_to_fs_path(uri, path):
    assert uris.to_fs_path(uri) == path


@windows_only
@pytest.mark.parametrize(
    "uri,path",
    [
        ("file:///c:/far/boo", "c:\\far\\boo"),
        ("file:///C:/far/boo", "c:\\far\\boo"),
        ("file:///C:/far/space%20%3Fboo", "c:\\far\\space ?boo"),
    ],
)
def test_win_to_fs_path(uri, path):
    assert uris.to_fs_path(uri) == path


@unix_only
@pytest.mark.parametrize(
    "path,uri",
    [
        ("/foo/bar", "file:///foo/bar"),
        ("/foo/space ?bar", "file:///foo/space%20%3Fbar"),
    ],
)
def test_from_fs_path(path, uri):
    assert uris.from_fs_path(path) == uri


@windows_only
@pytest.mark.parametrize(
    "path,uri",
    [
        ("c:\\far\\boo", "file:///c:/far/boo"),
        ("C:\\far\\space ?boo", "file:///c:/far/space%20%3Fboo"),
    ],
)
def test_win_from_fs_path(path, uri):
    assert uris.from_fs_path(path) == uri


@pytest.mark.parametrize(
    "uri,kwargs,new_uri",
    [
        ("file:///foo/bar", {"path": "/baz/boo"}, "file:///baz/boo"),
        (
            "file:///D:/hello%20world.py",
            {"path": "D:/hello universe.py"},
            "file:///d:/hello%20universe.py",
        ),
    ],
)
def test_uri_with(uri, kwargs, new_uri):
    assert uris.uri_with(uri, **kwargs) == new_uri
