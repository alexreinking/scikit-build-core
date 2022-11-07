from __future__ import annotations

import contextlib
import io
import os
import tarfile
from pathlib import Path

import pathspec
from pyproject_metadata import StandardMetadata

from .._compat import tomllib
from ..settings.skbuild_settings import read_settings
from .init import setup_logging

__all__: list[str] = ["build_sdist"]


def __dir__() -> list[str]:
    return __all__


def build_sdist(
    sdist_directory: str,
    # pylint: disable-next=unused-argument
    config_settings: dict[str, list[str] | str] | None = None,
) -> str:
    settings = read_settings(Path("pyproject.toml"), config_settings or {})
    setup_logging(settings.logging.level)

    sdist_dir = Path(sdist_directory)

    with Path("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    metadata = StandardMetadata.from_pyproject(pyproject)
    pkg_info = bytes(metadata.as_rfc822())

    srcdirname = f"{metadata.name}-{metadata.version}"
    filename = f"{srcdirname}.tar.gz"

    exclude_lines = [
        ".git/",
        ".tox/",
        ".nox/",
        ".egg-info/",
        "__pycache__/",
        "__pypackages__/",
    ]

    with contextlib.suppress(FileNotFoundError):
        with open(".gitignore", encoding="utf-8") as f:
            exclude_lines += f.readlines()

    exclude_spec = pathspec.GitIgnoreSpec.from_lines(exclude_lines)

    # TODO: support SOURCE_DATE_EPOCH for reproducible builds
    sdist_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(sdist_dir / filename, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for dirpath, _dirnames, filenames in os.walk("."):
            paths = (Path(dirpath) / fn for fn in filenames)
            if exclude_spec is not None:
                paths = (p for p in paths if not exclude_spec.match_file(p))
            for filepath in paths:
                tar.add(filepath, arcname=srcdirname / filepath)

        tarinfo = tarfile.TarInfo(name=f"{srcdirname}/PKG-INFO")
        tarinfo.size = len(pkg_info)
        with io.BytesIO(pkg_info) as fileobj:
            tar.addfile(tarinfo, fileobj)

    return filename
