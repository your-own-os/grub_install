#!/usr/bin/env python3

# grub_install - grub installation
#
# Copyright (c) 2020-2021 Fpemud <fpemud@sina.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
grub_install

@author: Fpemud
@license: GPLv3 License
@contact: fpemud@sina.com
"""


__author__ = "fpemud@sina.com (Fpemud)"
__version__ = "0.0.1"


from ._const import TargetType
from ._const import TargetAccessMode
from ._const import PlatformType
from ._const import PlatformInstallInfo
from ._const import RootfsPartitionOrBootPartitionMountPoint

from ._source import Source

from ._target import Target

from ._misc import GrubEnvFile
from ._misc import GrubCfgFile

from ._errors import SourceError
from ._errors import TargetError
from ._errors import InstallError
from ._errors import CopySourceError
from ._errors import CompareWithSourceError


__all__ = [
    "TargetType",
    "TargetAccessMode",
    "PlatformType",
    "PlatformInstallInfo",
    "RootfsPartitionOrBootPartitionMountPoint",
    "Source",
    "Target",
    "GrubEnvFile",
    "GrubCfgFile",
    "SourceError",
    "TargetError",
    "InstallError",
    "CopySourceError",
    "CompareWithSourceError",
]
