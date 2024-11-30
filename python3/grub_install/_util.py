#!/usr/bin/env python3

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


import os
import re
import shutil
import pathlib
import filecmp


def rel_path(baseDir, path):
    assert path.startswith(baseDir)
    return os.path.relpath(path, baseDir)


def force_rm(path):
    if os.path.islink(path):
        os.remove(path)
    elif os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.remove(path)             # other type of file, such as device node
    else:
        pass                        # path does not exist, do nothing


def force_mkdir(path, clear=False):
    if os.path.islink(path):
        os.remove(path)
        os.mkdir(path)
    elif os.path.isfile(path):
        os.remove(path)
        os.mkdir(path)
    elif os.path.isdir(path):
        if clear:
            shutil.rmtree(path)
            os.mkdir(path)
        else:
            pass
    elif os.path.lexists(path):
        os.remove(path)             # other type of file, such as device node
        os.mkdir(path)
    else:
        os.mkdir(path)              # path does not exist


def rmdir_if_empty(path):
    if os.path.exists(path):
        if len(os.listdir(path)) == 0:
            os.rmdir(path)


def shutil_copy_robust(*kargs, **kwargs):
    # FIXME: this is because fusefat does not support chmod, maybe we should modify fusefat
    try:
        shutil.copy(*kargs, **kwargs)
    except OSError as e:
        if e.errno == 38:
            # target filesystem does not support chmod operation
            pass
        else:
            raise


def compare_file_and_content(filepath, content):
    if isinstance(content, str):
        return pathlib.Path(filepath).read_text() == content
    if isinstance(content, bytes):
        return pathlib.Path(filepath).read_bytes() == content
    else:
        assert False


def compare_files(filepath1, filepath2):
    # don't use filecmp.cmp() directly
    # filecmp.dircmp is too complex, we created function compare_files() and compare_directories()
    return filecmp.cmp(filepath1, filepath2, shallow=False)


def compare_directories(dirpath1, dirpath2):
    ret1 = set(os.listdir(dirpath1))
    ret2 = set(os.listdir(dirpath2))
    if ret1 != ret2:
        return False
    for fn in ret1:
        if not filecmp.cmp(os.path.join(dirpath1, fn), os.path.join(dirpath2, fn), shallow=False):
            return False
    return True


def is_buffer_all_zero(buf):
    for b in buf:
        if b != 0:
            return False
    return True


class PartiUtil:

    @staticmethod
    def isDiskOrParti(devPath):
        if re.fullmatch("/dev/sd[a-z]", devPath) is not None:
            return True
        if re.fullmatch("(/dev/sd[a-z])([0-9]+)", devPath) is not None:
            return False
        if re.fullmatch("/dev/xvd[a-z]", devPath) is not None:
            return True
        if re.fullmatch("(/dev/xvd[a-z])([0-9]+)", devPath) is not None:
            return False
        if re.fullmatch("/dev/vd[a-z]", devPath) is not None:
            return True
        if re.fullmatch("(/dev/vd[a-z])([0-9]+)", devPath) is not None:
            return False
        if re.fullmatch("/dev/nvme[0-9]+n[0-9]+", devPath) is not None:
            return True
        if re.fullmatch("(/dev/nvme[0-9]+n[0-9]+)p([0-9]+)", devPath) is not None:
            return False
        assert False

    @staticmethod
    def partiToDiskAndPartiId(partitionDevPath):
        m = re.fullmatch("(/dev/sd[a-z])([0-9]+)", partitionDevPath)
        if m is not None:
            return (m.group(1), int(m.group(2)))
        m = re.fullmatch("(/dev/xvd[a-z])([0-9]+)", partitionDevPath)
        if m is not None:
            return (m.group(1), int(m.group(2)))
        m = re.fullmatch("(/dev/vd[a-z])([0-9]+)", partitionDevPath)
        if m is not None:
            return (m.group(1), int(m.group(2)))
        m = re.fullmatch("(/dev/nvme[0-9]+n[0-9]+)p([0-9]+)", partitionDevPath)
        if m is not None:
            return (m.group(1), int(m.group(2)))
        assert False

    @staticmethod
    def partiToDisk(partitionDevPath):
        return PartiUtil.partiToDiskAndPartiId(partitionDevPath)[0]

    @staticmethod
    def diskToParti(diskDevPath, partitionId):
        m = re.fullmatch("/dev/sd[a-z]", diskDevPath)
        if m is not None:
            return diskDevPath + str(partitionId)
        m = re.fullmatch("/dev/xvd[a-z]", diskDevPath)
        if m is not None:
            return diskDevPath + str(partitionId)
        m = re.fullmatch("/dev/vd[a-z]", diskDevPath)
        if m is not None:
            return diskDevPath + str(partitionId)
        m = re.fullmatch("/dev/nvme[0-9]+n[0-9]+", diskDevPath)
        if m is not None:
            return diskDevPath + "p" + str(partitionId)
        assert False

    @staticmethod
    def diskHasParti(diskDevPath, partitionId):
        partiDevPath = PartiUtil.diskToParti(diskDevPath, partitionId)
        return os.path.exists(partiDevPath)

    @staticmethod
    def diskHasMoreParti(diskDevPath, partitionId):
        for fn in os.listdir("/dev"):
            m = re.fullmatch(os.path.basename(diskDevPath) + "([0-9]+)", fn)
            if m is not None and int(m.group(1)) > partitionId:
                return True
        return False

    @staticmethod
    def partiExists(partitionDevPath):
        return os.path.exists(partitionDevPath)
