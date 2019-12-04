from __future__ import unicode_literals

import copy
from contextlib import contextmanager

from funcy import merge

from .local import DependencyLOCAL
from dvc.exceptions import NoOutputInExternalRepoError
from dvc.exceptions import FileOutsideRepoError
from dvc.external_repo import external_repo
from dvc.utils.compat import str


import os
import shutil


def copy_git_file(repo, src, dst):
    src_full_path = os.path.join(repo.root_dir, src)
    dst_full_path = os.path.abspath(dst)

    if repo.root_dir not in src_full_path:
        raise FileOutsideRepoError(src)

    if os.path.isdir(src_full_path):
        shutil.copytree(src_full_path, dst_full_path)
    else:
        shutil.copy2(src_full_path, dst_full_path)


class DependencyREPO(DependencyLOCAL):
    PARAM_REPO = "repo"
    PARAM_URL = "url"
    PARAM_REV = "rev"
    PARAM_REV_LOCK = "rev_lock"

    REPO_SCHEMA = {PARAM_URL: str, PARAM_REV: str, PARAM_REV_LOCK: str}

    def __init__(self, def_repo, stage, *args, **kwargs):
        self.def_repo = def_repo
        super(DependencyREPO, self).__init__(stage, *args, **kwargs)

    def _parse_path(self, remote, path):
        return None

    @property
    def is_in_repo(self):
        return False

    @property
    def repo_pair(self):
        d = self.def_repo
        return d[self.PARAM_URL], d[self.PARAM_REV_LOCK] or d[self.PARAM_REV]

    def __str__(self):
        return "{} ({})".format(self.def_path, self.def_repo[self.PARAM_URL])

    @contextmanager
    def _make_repo(self, **overrides):
        with external_repo(**merge(self.def_repo, overrides)) as repo:
            yield repo

    def status(self):
        with self._make_repo() as repo:
            current = repo.find_out_by_relpath(self.def_path).info

        with self._make_repo(rev_lock=None) as repo:
            updated = repo.find_out_by_relpath(self.def_path).info

        if current != updated:
            return {str(self): "update available"}

        return {}

    def save(self):
        pass

    def dumpd(self):
        return {self.PARAM_PATH: self.def_path, self.PARAM_REPO: self.def_repo}

    def fetch(self):
        with self._make_repo(
            cache_dir=self.repo.cache.local.cache_dir
        ) as repo:
            self.def_repo[self.PARAM_REV_LOCK] = repo.scm.get_rev()

            out = repo.find_out_by_relpath(self.def_path)
            with repo.state:
                repo.cloud.pull(out.get_used_cache())

        return out

    def download(self, to):
        try:
            out = self.fetch()
            to.info = copy.copy(out.info)
            to.checkout()
        except NoOutputInExternalRepoError:
            with self._make_repo(
                cache_dir=self.repo.cache.local.cache_dir
            ) as repo:
                copy_git_file(repo, self.def_path, to.fspath)

    def update(self):
        with self._make_repo(rev_lock=None) as repo:
            self.def_repo[self.PARAM_REV_LOCK] = repo.scm.get_rev()
