from __future__ import unicode_literals

import filecmp
import os

import pytest

from dvc.config import Config
from dvc.exceptions import GetDVCFileError
from dvc.exceptions import UrlNotDvcRepoError
from dvc.repo import Repo
from dvc.system import System
from dvc.utils import makedirs
from tests.utils import trees_equal


def test_get_repo_file(erepo):
    src = erepo.FOO
    dst = erepo.FOO + "_imported"

    Repo.get(erepo.root_dir, src, dst)

    assert os.path.exists(dst)
    assert os.path.isfile(dst)
    assert filecmp.cmp(erepo.FOO, dst, shallow=False)


def test_get_repo_dir(erepo):
    src = erepo.DATA_DIR
    dst = erepo.DATA_DIR + "_imported"

    Repo.get(erepo.root_dir, src, dst)

    assert os.path.exists(dst)
    assert os.path.isdir(dst)
    trees_equal(src, dst)


def test_get_regular_file(erepo):
    src = os.path.join(erepo.root_dir, "some_file")
    dst = os.path.join(os.getcwd(), "_imported")

    erepo.create(src, "hello")
    erepo.dvc.scm.add([src])
    erepo.dvc.scm.commit("add a regular file")
    Repo.get(erepo.root_dir, os.path.basename(src), os.path.basename(dst))

    assert os.path.exists(dst)
    assert os.path.isfile(dst)
    assert filecmp.cmp(src, dst, shallow=False)


def test_get_regular_dir(erepo):
    src = os.path.join(erepo.root_dir, "some_directory")
    src_file = os.path.join(src, "file.txt")
    dst = os.path.join(os.getcwd(), "_imported")

    erepo.create(src_file, "hello")
    erepo.dvc.scm.add([src_file])
    erepo.dvc.scm.commit("add a regular dir")
    Repo.get(erepo.root_dir, os.path.basename(src), os.path.basename(dst))

    assert os.path.exists(dst)
    assert os.path.isdir(dst)
    trees_equal(src, dst)


def test_cache_type_is_properly_overridden(repo_dir, erepo):
    erepo.dvc.config.set(
        Config.SECTION_CACHE, Config.SECTION_CACHE_TYPE, "symlink"
    )
    erepo.dvc.scm.add([erepo.dvc.config.config_file])
    erepo.dvc.scm.commit("set cache type to symlinks")

    src = erepo.FOO
    dst = erepo.FOO + "_imported"

    Repo.get(erepo.root_dir, src, dst)

    assert not System.is_symlink(dst)
    assert os.path.exists(dst)
    assert os.path.isfile(dst)


def test_get_repo_rev(erepo):
    src = "version"
    dst = src

    Repo.get(erepo.root_dir, src, dst, rev="branch")

    assert os.path.exists(dst)
    assert os.path.isfile(dst)
    with open(dst, "r+") as fobj:
        assert fobj.read() == "branch"


def test_get_from_non_dvc_repo(git_erepo):
    with pytest.raises(UrlNotDvcRepoError):
        Repo.get(git_erepo.root_dir, "some_file.zip")


def test_get_a_dvc_file(erepo):
    with pytest.raises(GetDVCFileError):
        Repo.get(erepo.root_dir, "some_file.dvc")


@pytest.mark.parametrize("dname", [".", "dir", "dir/subdir"])
def test_get_to_dir(dname, erepo):
    src = erepo.FOO

    makedirs(dname, exist_ok=True)

    Repo.get(erepo.root_dir, src, dname)

    dst = os.path.join(dname, os.path.basename(src))

    assert os.path.isdir(dname)
    assert filecmp.cmp(erepo.FOO, dst, shallow=False)
