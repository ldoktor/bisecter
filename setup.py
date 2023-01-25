#!/bin/env python3
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2023
# Author: Lukas Doktor <ldoktor@redhat.com>

import os
import shutil
import subprocess   # nosec

from setuptools import setup, find_packages

# pylint: disable=E0611
SETUP_PATH = os.path.abspath(os.path.dirname(__file__))


def _get_git_version():
    """
    Get version from git describe

    :warning: This implementation must match the "bisecter/version.py" one
    """
    curdir = os.getcwd()
    try:
        os.chdir(SETUP_PATH)
        git = shutil.which("git")
        version = subprocess.check_output(  # nosec
            [git, "describe", "--tags",
             "HEAD"]).strip().decode("utf-8")
        if version.count("-") == 2:
            split = version.split('-')
            version = "%s.%s+%s" % tuple(split)
        else:
            version = version.replace("-", ".")
        try:
            subprocess.check_output([git, "diff", "--quiet"])  # nosec
        except subprocess.CalledProcessError:
            version += "+dirty"
    except (OSError, subprocess.SubprocessError, NameError):
        return '0.0'
    finally:
        os.chdir(curdir)
    return version


def get_long_description():
    with open(os.path.join(SETUP_PATH, 'README.rst'), 'r') as req:
        req_contents = req.read()
    return req_contents


if __name__ == '__main__':
    setup(name='bisecter',
          version=_get_git_version(),
          description='TODO',
          long_description=get_long_description(),
          long_description_content_type="text/markdown",
          author='Lukas Doktor',
          author_email='ldoktor@redhat.com',
          url='https://github.com/distributed-system-analysis/bisecter',
          license="GPLv2+",
          classifiers=[
              "Development Status :: 2 - Pre-Alpha",
              "Intended Audience :: Developers",
              "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
              "Natural Language :: English",
              "Operating System :: POSIX",
              "Topic :: Software Development :: Testing",
              "Programming Language :: Python :: 3",
              ],
          packages=find_packages(exclude=('selftests*',)),
          include_package_data=True,
          scripts=['scripts/bisecter'],
          test_suite='selftests',
          python_requires='>=3.5',
          install_requires=['PyYAML'])
