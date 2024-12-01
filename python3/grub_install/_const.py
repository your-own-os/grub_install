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


import enum


class TargetType(enum.Enum):
    MOUNTED_HDD_DEV = enum.auto()            # hard-disk device
    PYCDLIB_OBJ = enum.auto()                # pycdlib object
    ISO_DIR = enum.auto()                    # directory containing files for a ISO


class TargetAccessMode(enum.Enum):
    R = enum.auto()
    RW = enum.auto()
    W = enum.auto()


class PlatformType(enum.Enum):
    I386_PC = "i386-pc"
    I386_EFI = "i386-efi"
    I386_QEMU = "i386-qemu"
    I386_COREBOOT = "i386-coreboot"
    I386_MULTIBOOT = "i386-multiboot"
    I386_IEEE1275 = "i386-ieee1275"
    I386_XEN = "i386-xen"
    I386_XEN_PVH = "i386-xen_pvh"
    X86_64_EFI = "x86_64-efi"
    X86_64_XEN = "x86_64_xen"
    ARM_UBOOT = "arm-uboot"
    ARM_COREBOOT = "arm-coreboot"
    ARM_EFI = "arm-efi"
    ARM64_EFI = "arm64-efi"
    IA64_EFI = "ia64-efi"
    POWERPC_IEEE1275 = "powerpc-ieee1275"
    SPARC64_IEEE1275 = "sparc64-ieee1275"
    MIPS_ARC = "mips-arc"
    MIPS_QEMU_MIPS = "mips_qemu-mips"           # FIXME
    MIPSEL_ARC = "mipsel-arc"
    MIPSEL_LOONGSON = "mipsel-loongson"
    MIPSEL_QEMU_MIPS = "mipsel_qemu-mips"       # FIXME
    RISCV32_EFI = "riscv32-efi"
    RISCV64_EFI = "riscv64-efi"


class PlatformInstallInfo:

    class Status(enum.Enum):
        NORMAL = enum.auto()
        NOT_VALID = enum.auto()
        NOT_INSTALLED = enum.auto()

    def __init__(self):
        self.status = None

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.__dict__)


class RootfsPartitionOrBootPartitionMountPoint:

    def __init__(self, disk, partition, mountpoint, fstype, opts, rootfs_partition_or_boot_partition, is_disk_removable):
        assert disk != partition

        self._disk = disk
        self._partition = partition
        self._mountpoint = mountpoint
        self._fstype = fstype
        self._opts = opts
        self._rootfsOrBoot = rootfs_partition_or_boot_partition
        self._isRemovable = is_disk_removable

    @property
    def disk(self):
        return self._disk

    @property
    def partition(self):
        return self._partition

    @property
    def mountpoint(self):
        return self._mountpoint

    @property
    def fstype(self):
        return self._fstype

    @property
    def opts(self):
        return self._opts

    def is_rootfs_mount_point(self):
        return self._rootfsOrBoot

    def is_boot_mount_point(self):
        return not self._rootfsOrBoot

    def is_disk_removable(self):
        return self._isRemovable


#    MOUNTED_FDD_DEV = enum.auto()            # floppy device
#    MOUNTED_HDD_DEV_APPLE = enum.auto()      # apple device
#    APPLE_ISO_DIR = enum.auto()              # apple device
