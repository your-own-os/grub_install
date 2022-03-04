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


from ._const import PlatformType


class Handy:

    GRUB_DISK_SECTOR_SIZE = 0x200

    # The offset of the start of BPB (BIOS Parameter Block).
    GRUB_BOOT_MACHINE_BPB_START	= 0x3

    # The offset of the end of BPB (BIOS Parameter Block).
    GRUB_BOOT_MACHINE_BPB_END = 0x5a

    # The offset of BOOT_DRIVE_CHECK.
    GRUB_BOOT_MACHINE_DRIVE_CHECK = 0x66

    # The offset of a magic number used by Windows NT.
    GRUB_BOOT_MACHINE_WINDOWS_NT_MAGIC = 0x1b8

    # The offset of the start of the partition table.
    GRUB_BOOT_MACHINE_PART_START = 0x1be

    # The offset of the end of the partition table.
    GRUB_BOOT_MACHINE_PART_END = 0x1fe

    GRUB_KERNEL_I386_PC_LINK_ADDR = 0x9000

    @staticmethod
    def isPlatformEfi(platform_type):
        return platform_type in [
            PlatformType.I386_EFI,
            PlatformType.X86_64_EFI,
            PlatformType.IA64_EFI,
            PlatformType.ARM_EFI,
            PlatformType.ARM64_EFI,
            PlatformType.RISCV32_EFI,
            PlatformType.RISCV64_EFI
        ]

    @staticmethod
    def isPlatformCoreboot(platform_type):
        return platform_type in [
            PlatformType.I386_COREBOOT,
            PlatformType.ARM_COREBOOT,
        ]
    
    @staticmethod
    def isPlatformXen(platform_type):
        return platform_type in [
            PlatformType.I386_XEN,
            PlatformType.I386_XEN_PVH,
            PlatformType.X86_64_XEN,
        ]

    @staticmethod
    def isPlatformIeee1275(platform_type):
        return platform_type in [
            PlatformType.I386_IEEE1275,
            PlatformType.POWERPC_IEEE1275,
            PlatformType.SPARC64_IEEE1275,
        ]

    @staticmethod
    def getStandardEfiFile(platform_type):
        # The specification makes stricter requirements of removable
        #  devices, in order that only one image can be automatically loaded
        #  from them.  The image must always reside under /EFI/BOOT, and it
        #  must have a specific file name depending on the architecture.

        if platform_type == PlatformType.I386_EFI:
            return "BOOTIA32.EFI"
        if platform_type == PlatformType.X86_64_EFI:
            return "BOOTX64.EFI"
        if platform_type == PlatformType.IA64_EFI:
            return "BOOTIA64.EFI"
        if platform_type == PlatformType.ARM_EFI:
            return "BOOTARM.EFI"
        if platform_type == PlatformType.ARM64_EFI:
            return "BOOTAA64.EFI"
        if platform_type == PlatformType.RISCV32_EFI:
            return "BOOTRISCV32.EFI"
        if platform_type == PlatformType.RISCV64_EFI:
            return "BOOTRISCV64.EFI"
        assert False
