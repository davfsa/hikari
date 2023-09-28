# -*- coding: utf-8 -*-
# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021-present davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pathlib

from pipelines import config
from pipelines import nox

VERSION_REQUIREMENT = "3.9,<3.12"


@nox.session()
def generate_locks(session: nox.Session) -> None:
    """Generate lock files for the dev-requirements."""
    nox.install_dev_requirements(session, "piplock")

    for path in pathlib.Path(config.DEV_REQUIREMENTS_DIRECTORY).glob("*.in"):
        session.run(
            "pip-compile-cross-platform",
            str(path),
            "-o",  # --output-file
            str(path.with_suffix(".txt")),
            "--min-python-version",
            VERSION_REQUIREMENT,
        )
