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
import glob
import shutil
import struct
import parted
import pathlib
import reedsolo
from ._util import rel_path, force_rm, force_mkdir, rmdir_if_empty, shutil_copy_robust, compare_file_and_content, compare_files, compare_directories, is_buffer_all_zero, PartiUtil
from ._const import TargetType, TargetAccessMode, PlatformType, PlatformInstallInfo
from ._errors import TargetError, InstallError, CompareWithSourceError
from ._handy import Handy, Grub, GrubMountPoint
from ._source import Source


class Target:

    def __init__(self, target_type, target_access_mode, **kwargs):
        assert isinstance(target_type, TargetType)
        assert isinstance(target_access_mode, TargetAccessMode)

        self._targetType = target_type
        self._mode = target_access_mode
        self._tmpDir = kwargs.get("tmp_work_dir", None)

        # target specific variables
        if self._targetType == TargetType.MOUNTED_HDD_DEV:
            rootfsMnt = kwargs.get("rootfs_mount_point", None)
            if rootfsMnt is not None:
                assert rootfsMnt.is_rootfs_mount_point()
            bootMnt = kwargs.get("boot_mount_point", None)
            if bootMnt is not None:
                assert bootMnt.is_boot_mount_point()
            if bootMnt is not None:
                if rootfsMnt is not None:
                    assert os.path.join(rootfsMnt.mountpoint, "boot") == bootMnt.mountpoint
                self._mnt = GrubMountPoint(bootMnt)
                self._bootDir = self._mnt.mountpoint
            elif rootfsMnt is not None:
                self._mnt = GrubMountPoint(rootfsMnt)
                self._bootDir = os.path.join(self._mnt.mountpoint, "boot")
                if not os.path.exists(self._bootDir):
                    raise TargetError("boot directory \"%s\" does not exist" % (self._bootDir))
            else:
                assert False
            if self._mnt.fs_uuid is None:
                raise TargetError("no fsuuid found")
        elif self._targetType == TargetType.PYCDLIB_OBJ:
            assert self._mode in [TargetAccessMode.R, TargetAccessMode.W]
            self._iso = kwargs.get["obj"]
        elif self._targetType == TargetType.ISO_DIR:
            self._dir = kwargs["dir"]
            self._bootDir = os.path.join(self._dir, "boot")
        else:
            assert False

        # fill self._platforms
        self._platforms = dict()
        if self._mode in [TargetAccessMode.R, TargetAccessMode.RW]:
            if self._targetType == TargetType.MOUNTED_HDD_DEV:
                _Common.init_platforms(self)
                for k, v in self._platforms.items():
                    try:
                        if k == PlatformType.I386_PC:
                            _Bios.fill_platform_install_info_with_mbr(k, v, self._bootDir, self._mnt.disk)
                        elif Handy.isPlatformEfi(k):
                            _Efi.fill_platform_install_info(k, v, self._targetType, self._bootDir)
                        else:
                            assert False
                    except TargetError as e:
                        self._platforms[k] = _newNotValidPlatformInstallInfo(str(e))
            elif self._targetType == TargetType.PYCDLIB_OBJ:
                _PyCdLib.init_platforms(self)
                for k, v in self._platforms.items():
                    try:
                        if k == PlatformType.I386_PC:
                            # FIXME
                            assert False
                        elif Handy.isPlatformEfi(k):
                            # FIXME
                            assert False
                        else:
                            assert False
                    except TargetError as e:
                        self._platforms[k] = _newNotValidPlatformInstallInfo(str(e))
            elif self._targetType == TargetType.ISO_DIR:
                _Common.init_platforms(self)
                for k, v in self._platforms.items():
                    try:
                        if k == PlatformType.I386_PC:
                            _Bios.fill_platform_install_info_without_mbr(k, v, self._bootDir)
                        elif Handy.isPlatformEfi(k):
                            _Efi.fill_platform_install_info(k, v, self._targetType, self._bootDir)
                        else:
                            assert False
                    except TargetError as e:
                        self._platforms[k] = _newNotValidPlatformInstallInfo(str(e))
            else:
                assert False

    @property
    def target_type(self):
        return self._targetType

    @property
    def target_access_mode(self):
        return self._mode

    @property
    def platforms(self):
        return [k for k, v in self._platforms.items() if v.status == PlatformInstallInfo.Status.NORMAL]

    def get_platform_install_info(self, platform_type):
        assert isinstance(platform_type, PlatformType)

        if platform_type in self._platforms:
            return self._platforms[platform_type]
        else:
            return _newNotInstalledPlatformInstallInfo()

    def install_platform(self, platform_type, source, **kwargs):
        assert self._mode in [TargetAccessMode.RW, TargetAccessMode.W]
        assert isinstance(platform_type, PlatformType)
        assert isinstance(source, Source)

        ret = PlatformInstallInfo()
        ret.status = PlatformInstallInfo.Status.NORMAL

        if self._targetType == TargetType.MOUNTED_HDD_DEV:
            if platform_type == PlatformType.I386_PC:
                _Common.install_platform(self, platform_type, source,
                                         tmpDir=self._tmpDir,
                                         debugImage=kwargs.get("debug_image", None))
                _Bios.install_with_mbr(platform_type, ret, source, self._bootDir, self._mnt.disk,
                                       False,                                                           # bFloppyOrHdd
                                       kwargs.get("allow_floppy", False),                               # bAllowFloppy
                                       kwargs.get("bpb", True),                                         # bBpb
                                       kwargs.get("rs_codes", True))                                    # bAddRsCodes
            elif Handy.isPlatformEfi(platform_type):
                assert self._mnt.is_boot_mount_point()
                if self._mnt.grub_fs != "fat":
                    raise InstallError("%s must be fat filesystem" % (self._mnt.mountpoint))
                _Common.install_platform(self, platform_type, source,
                                         tmpDir=self._tmpDir,
                                         debugImage=kwargs.get("debug_image", None))
                _Efi.install_info_efi_dir(platform_type, ret, self._bootDir,
                                          kwargs.get("removable", False),                               # bRemovable
                                          kwargs.get("update_nvram", True))                             # bUpdateNvram
            else:
                assert False
        elif self._targetType == TargetType.PYCDLIB_OBJ:
            # FIXME
            assert False
        elif self._targetType == TargetType.ISO_DIR:
            _Common.install_platform(self, platform_type, source,
                                     tmpDir=self._tmpDir,
                                     debugImage=kwargs.get("debug_image", None))
            if platform_type == PlatformType.I386_PC:
                _Bios.install_without_mbr(platform_type, ret, source, self._bootDir)
            elif Handy.isPlatformEfi(platform_type):
                _Efi.install_info_efi_dir(platform_type, ret, self._bootDir,
                                          kwargs.get("removable", False),                               # bRemovable
                                          False)                                                        # bUpdateNvram
            else:
                assert False
        else:
            assert False

        self._platforms[platform_type] = ret

    def remove_platform(self, platform_type):
        assert self._mode in [TargetAccessMode.RW, TargetAccessMode.W]
        assert isinstance(platform_type, PlatformType)

        # do nothing if the specified platform does not exists
        if platform_type not in self._platforms:
            return

        # do remove
        if self._targetType == TargetType.MOUNTED_HDD_DEV:
            if platform_type == PlatformType.I386_PC:
                _Bios.remove_from_mbr(platform_type, self._mnt.disk)
            elif Handy.isPlatformEfi(platform_type):
                _Efi.remove_from_efi_dir(platform_type, self._bootDir)
            else:
                assert False
            _Common.remove_platform(self, platform_type)
        elif self._targetType == TargetType.PYCDLIB_OBJ:
            # FIXME
            assert False
        elif self._targetType == TargetType.ISO_DIR:
            if platform_type == PlatformType.I386_PC:
                pass
            elif Handy.isPlatformEfi(platform_type):
                _Efi.remove_from_efi_dir(platform_type, self._bootDir)
            else:
                assert False
            _Common.remove_platform(self, platform_type)
        else:
            assert False

        # delete PlatformInstallInfo object
        del self._platforms[platform_type]

    def install_data_files(self, source, locales=None, fonts=None, themes=None):
        assert self._mode in [TargetAccessMode.RW, TargetAccessMode.W]
        if locales is not None:
            assert source.supports(source.CAP_NLS)
        if fonts is not None:
            assert source.supports(source.CAP_FONTS)
        if themes is not None:
            assert source.supports(source.CAP_THEMES)

        grubDir = os.path.join(self._bootDir, "grub")
        force_mkdir(grubDir)

        if locales is not None:
            dstDir = os.path.join(grubDir, "locale")
            force_mkdir(dstDir, clear=True)
            if locales == "*":
                for lname, fullfn in source.get_all_locale_files().items():
                    shutil_copy_robust(fullfn, os.path.join(dstDir, "%s.mo" % (lname)))
            else:
                for lname in locales:
                    shutil_copy_robust(source.get_locale_file(lname), "%s.mo" % (lname))

        if fonts is not None:
            dstDir = os.path.join(grubDir, "fonts")
            force_mkdir(dstDir, clear=True)
            if fonts == "*":
                for fname, fullfn in source.get_all_font_files().items():
                    shutil_copy_robust(fullfn, dstDir)
            else:
                for fname in fonts:
                    shutil_copy_robust(source.get_font_file(fname), dstDir)

        if themes is not None:
            dstDir = os.path.join(grubDir, "themes")
            force_mkdir(dstDir, clear=True)
            if themes == "*":
                for tname, fullfn in source.get_all_theme_directories().items():
                    shutil.copytree(fullfn, os.path.join(dstDir, tname), copy_function=shutil_copy_robust)
            else:
                for tname in themes:
                    shutil.copytree(source.get_theme_directory(tname), dstDir, copy_function=shutil_copy_robust)

    def remove_data_files(self):
        assert self._mode in [TargetAccessMode.RW, TargetAccessMode.W]

        grubDir = os.path.join(self._bootDir, "grub")
        force_rm(os.path.join(grubDir, "locale"))
        force_rm(os.path.join(grubDir, "fonts"))
        force_rm(os.path.join(grubDir, "themes"))

    def remove_all(self):
        assert self._mode in [TargetAccessMode.RW, TargetAccessMode.W]

        # remove platforms, some platform needs special processing
        for k in list(self._platforms.keys()):
            self.remove_platform(k)

        # remove remaining files
        if self._targetType == TargetType.MOUNTED_HDD_DEV:
            _Efi.remove_remaining_crufts(self._bootDir)
        elif self._targetType == TargetType.PYCDLIB_OBJ:
            # FIXME
            assert False
        elif self._targetType == TargetType.ISO_DIR:
            _Efi.remove_remaining_crufts(self._bootDir)
        else:
            assert False
        _Common.remove_remaining_crufts(self)

    def compare_with_source(self, source):
        assert self._mode in [TargetAccessMode.R, TargetAccessMode.RW]
        assert isinstance(source, Source)

        for pt in self._platforms:
            if self._targetType == TargetType.MOUNTED_HDD_DEV:
                restFiles = _Common.check_platform(self, pt, source, tmpDir=self._tmpDir)
                if pt == PlatformType.I386_PC:
                    _Bios.check_rest_files(pt, source, self._bootDir, restFiles)
                elif Handy.isPlatformEfi(pt):
                    pass
                else:
                    assert False
            elif self._targetType == TargetType.PYCDLIB_OBJ:
                # FIXME
                assert False
            elif self._targetType == TargetType.ISO_DIR:
                restFiles = _Common.check_platform(self, pt, source, tmpDir=self._tmpDir)
                if pt == PlatformType.I386_PC:
                    _Bios.check_rest_files(pt, source, self._bootDir, restFiles)
                elif Handy.isPlatformEfi(pt):
                    pass
                else:
                    assert False
            else:
                assert False

        _Common.check_data(self, source)


class _Common:

    @staticmethod
    def init_platforms(p):
        grubDir = os.path.join(p._bootDir, "grub")
        if os.path.isdir(grubDir):
            for fn in os.listdir(grubDir):
                try:
                    obj = PlatformInstallInfo()
                    obj.status = PlatformInstallInfo.Status.NORMAL
                    p._platforms[PlatformType(fn)] = obj
                except ValueError:
                    pass

    @staticmethod
    def install_platform(p, platform_type, source, tmpDir=None, debugImage=None):
        assert p._mnt.fs_uuid is not None

        grubDir = os.path.join(p._bootDir, "grub")
        platDirSrc = source.get_platform_directory(platform_type)
        platDirDst = os.path.join(grubDir, platform_type.value)

        # get module list and hints
        moduleList, hints = Grub.getModuleListAndHnits(platform_type, p._mnt)

        # install module files
        # FIXME: install only required modules
        if True:
            force_mkdir(grubDir)
            force_mkdir(platDirDst, clear=True)

            def __copy(fullfn, dstDir):
                # FIXME: specify owner, group, mode?
                shutil_copy_robust(fullfn, platDirDst)

            # copy module files
            for fullfn in glob.glob(os.path.join(platDirSrc, "*.mod")):
                __copy(fullfn, platDirDst)

            # copy other files
            for fn in Grub.PLATFORM_ADDON_FILES:
                __copy(os.path.join(platDirSrc, fn), platDirDst)

            # copy optional files
            for fn in Grub.PLATFORM_OPTIONAL_ADDON_FILES:
                fullfn = os.path.join(platDirSrc, fn)
                if os.path.exists(fullfn):
                    __copy(fullfn, platDirDst)

        # make core.img
        coreName, mkimageTarget = Grub.getCoreImgNameAndTarget(platform_type)
        coreBuf = Grub.makeCoreImage(source, platform_type, mkimageTarget, moduleList, p._mnt.fs_uuid,
                                     hints, rel_path(p._mnt.mountpoint, grubDir), debugImage, tmpDir=tmpDir)
        with open(os.path.join(platDirDst, coreName), "wb") as f:
            f.write(coreBuf)

    @staticmethod
    def remove_platform(p, platform_type):
        platDir = os.path.join(p._bootDir, "grub", platform_type.value)
        force_rm(platDir)

    @staticmethod
    def remove_remaining_crufts(p):
        force_rm(os.path.join(p._bootDir, "grub"))

    @staticmethod
    def check_platform(p, platform_type, source, tmpDir=None):
        grubDir = os.path.join(p._bootDir, "grub")
        platDirSrc = source.get_platform_directory(platform_type)
        platDirDst = os.path.join(p._bootDir, "grub", platform_type.value)
        assert os.path.exists(platDirDst)

        fileSet = set()

        # check module files
        if True:
            def __check(fullfn, fullfn2):
                # FIXME: check owner, group, mode?
                if not os.path.exists(fullfn2):
                    raise CompareWithSourceError("%s does not exist" % (fullfn2))
                if not compare_files(fullfn, fullfn2):
                    raise CompareWithSourceError("%s and %s are different" % (fullfn, fullfn2))
                fileSet.add(fullfn2)

            # check module files
            for fullfn in glob.glob(os.path.join(platDirSrc, "*.mod")):
                __check(fullfn, os.path.join(platDirDst, os.path.basename(fullfn)))

            # check addon files
            for fn in Grub.PLATFORM_ADDON_FILES:
                __check(os.path.join(platDirSrc, fn), os.path.join(platDirDst, fn))

            # check optional addon files
            for fn in Grub.PLATFORM_OPTIONAL_ADDON_FILES:
                fullfn, fullfn2 = os.path.join(platDirSrc, fn), os.path.join(platDirDst, fn)
                if os.path.exists(fullfn):
                    __check(fullfn, fullfn2)

        # check core.img
        bSame = False
        for debugImage in [False, True]:
            moduleList, hints = Grub.getModuleListAndHnits(platform_type, p._mnt)
            coreName, mkimageTarget = Grub.getCoreImgNameAndTarget(platform_type)
            coreBuf = Grub.makeCoreImage(source, platform_type, mkimageTarget, moduleList, p._mnt.fs_uuid,
                                         hints, rel_path(p._mnt.mountpoint, grubDir), debugImage, tmpDir=tmpDir)
            coreImgPath = os.path.join(platDirDst, coreName)
            if not compare_file_and_content(coreImgPath, coreBuf):
                fileSet.add(coreImgPath)
                bSame = True
                break
        if not bSame:
            raise CompareWithSourceError("%s and %s are different" % (fullfn, fullfn2))

        # check redundant
        return set(glob.glob(os.path.join(platDirDst, "*"))) - fileSet

    @staticmethod
    def check_data(p, source):
        localeDir = os.path.join(p._bootDir, "grub", "locale")
        if os.path.exists(localeDir):
            if not source.supports(source.CAP_NLS):
                raise CompareWithSourceError("NLS is not supported")
            for fn2 in os.listdir(localeDir):
                fullfn2 = os.path.join(localeDir, fn2)
                if fn2.endswith(".mo"):
                    lname = fn2.replace(".mo", "")
                    fullfn = source.try_get_locale_file(lname)
                    if fullfn is not None:
                        if not compare_files(fullfn, fullfn2):
                            raise CompareWithSourceError("%s and %s are different" % (fullfn, fullfn2))
                        continue
                raise CompareWithSourceError("redundant file %s found" % (fullfn2))

        fontsDir = os.path.join(p._bootDir, "grub", "fonts")
        if os.path.exists(fontsDir):
            if not source.supports(source.CAP_FONTS):
                raise CompareWithSourceError("fonts is not supported")
            for fullfn2 in glob.glob(os.path.join(fontsDir, "*.pf2")):
                fname = os.path.basename(fullfn2).replace(".pf2", "")
                fullfn = source.try_get_font_file(fname)
                if fullfn is not None:
                    if not compare_files(fullfn, fullfn2):
                        raise CompareWithSourceError("%s and %s are different" % (fullfn, fullfn2))
                    continue
                raise CompareWithSourceError("redundant file %s found" % (fullfn2))

        themesDir = os.path.join(p._bootDir, "grub", "themes")
        if os.path.exists(themesDir):
            if not source.supports(source.CAP_THEMES):
                raise CompareWithSourceError("themes is not supported")
            for tname in os.listdir(themesDir):
                fullfn2 = os.path.join(themesDir, tname)
                if os.path.isdir(fullfn2):
                    fullfn = source.try_get_theme_directory(tname)
                    if fullfn is not None:
                        if not compare_directories(fullfn, fullfn2):
                            raise CompareWithSourceError("%s and %s are different" % (fullfn, fullfn2))
                        continue
                raise CompareWithSourceError("redundant file %s found" % (fullfn2))


class _Bios:

    @classmethod
    def fill_platform_install_info_without_mbr(cls, platform_type, platform_install_info, bootDir):
        cls._checkAndReadBootImg(platform_type, bootDir, TargetError)
        cls._checkAndReadCoreImg(platform_type, bootDir, TargetError)

        platform_install_info.mbr_installed = False
        platform_install_info.allow_floppy = True
        platform_install_info.bpb = True
        platform_install_info.rs_codes = True

    @classmethod
    def fill_platform_install_info_with_mbr(cls, platform_type, platform_install_info, bootDir, dev):
        bootBuf = bytearray(cls._checkAndReadBootImg(platform_type, bootDir, TargetError))     # bootBuf needs to be writable
        coreBuf = cls._checkAndReadCoreImg(platform_type, bootDir, TargetError)

        # read MBR and MBR-gap
        tmpBootBuf, tmpRestBuf = None, None
        cls._checkDisk(dev, TargetError)
        with open(dev, "rb") as f:
            tmpBootBuf = f.read(len(bootBuf))
            tmpRestBuf = f.read(cls._getCoreBufMaxSize() - len(bootBuf))

        # boot.img and core.img is not installed
        if tmpBootBuf == cls._getAllZeroBootBuf(tmpBootBuf) and is_buffer_all_zero(tmpRestBuf):
            raise TargetError("boot.img and core.img are not installed to disk")

        # compare boot.img
        if True:
            # see comment in cls.install_into_mbr()
            s, e = Grub.BOOT_MACHINE_BPB_START, Grub.BOOT_MACHINE_BPB_END
            if not is_buffer_all_zero(tmpBootBuf[s:e]):
                bootBuf[s:e] = tmpBootBuf[s:e]
                bBpb = True
            else:
                bBpb = False

            # see comment in cls.install_into_mbr()
            s, e = Grub.BOOT_MACHINE_DRIVE_CHECK, Grub.BOOT_MACHINE_DRIVE_CHECK + 2
            if tmpBootBuf[s:e] == b'\x90\x90':
                bootBuf[s:e] = tmpBootBuf[s:e]
                bAllowFloppy = False
            else:
                bAllowFloppy = True

            # see comment in cls.install_into_mbr()
            s, e = Grub.BOOT_MACHINE_WINDOWS_NT_MAGIC, Grub.BOOT_MACHINE_PART_END
            bootBuf[s:e] = tmpBootBuf[s:e]

            # do compare
            if tmpBootBuf != bootBuf:
                raise TargetError("invalid MBR record content")

        # compare core.img
        if tmpRestBuf[:len(coreBuf)] == coreBuf:
            bRsCodes = False
        else:
            coreBuf = cls._getRsEncodedCoreBuf(coreBuf, Handy.isPlatformBigEndianOrLittleEndian(platform_type))
            if tmpRestBuf[:len(coreBuf)] == coreBuf:
                bRsCodes = True
            else:
                raise TargetError("invalid on-disk core.img content")

        # compare rest bytes
        if not is_buffer_all_zero(tmpRestBuf):
            raise TargetError("disk content after core.img should be all zero")

        # return
        platform_install_info.mbr_installed = True
        platform_install_info.allow_floppy = bAllowFloppy
        platform_install_info.bpb = bBpb
        platform_install_info.rs_codes = bRsCodes

    @classmethod
    def install_without_mbr(cls, platform_type, platform_install_info, source, bootDir):
        # copy boot.img
        shutil_copy_robust(os.path.join(source.get_platform_directory(platform_type), "boot.img"), os.path.join(bootDir, "grub", platform_type.value))

        # fill custom attributes
        platform_install_info.mbr_installed = False
        platform_install_info.allow_floppy = True
        platform_install_info.bpb = True
        platform_install_info.rs_codes = False

    @classmethod
    def install_with_mbr(cls, platform_type, platform_install_info, source, bootDir, dev, bFloppyOrHdd, bAllowFloppy, bBpb, bAddRsCodes):
        assert not bFloppyOrHdd and not bAllowFloppy        # FIXME

        # copy boot.img
        shutil_copy_robust(os.path.join(source.get_platform_directory(platform_type), "boot.img"), os.path.join(bootDir, "grub", platform_type.value))

        bootBuf = bytearray(cls._checkAndReadBootImg(platform_type, bootDir, InstallError))     # bootBuf needs to be writable
        coreBuf = cls._checkAndReadCoreImg(platform_type, bootDir, InstallError)
        cls._checkDisk(dev, InstallError)

        with open(dev, "rb+") as f:
            tmpBootBuf = f.read(len(bootBuf))

            # prepare bootBuf
            if True:
                # Copy the possible DOS BPB.
                if bBpb:
                    s, e = Grub.BOOT_MACHINE_BPB_START, Grub.BOOT_MACHINE_BPB_END
                    bootBuf[s:e] = tmpBootBuf[s:e]

                # If DEST_DRIVE is a hard disk, enable the workaround, which is
                # for buggy BIOSes which don't pass boot drive correctly. Instead,
                # they pass 0x00 or 0x01 even when booted from 0x80.
                if not bAllowFloppy and not bFloppyOrHdd:
                    # Replace the jmp (2 bytes) with double nop's.
                    s, e = Grub.BOOT_MACHINE_DRIVE_CHECK, Grub.BOOT_MACHINE_DRIVE_CHECK + 2
                    bootBuf[s:e] == b'\x90\x90'

                # Copy the partition table.
                if not bAllowFloppy and not bFloppyOrHdd:
                    s, e = Grub.BOOT_MACHINE_WINDOWS_NT_MAGIC, Grub.BOOT_MACHINE_PART_END
                    bootBuf[s:e] = tmpBootBuf[s:e]

            # prepare coreBuf
            if bAddRsCodes:
                coreBuf = cls._getRsEncodedCoreBuf(coreBuf, Handy.isPlatformBigEndianOrLittleEndian(platform_type))

            # write up to cls._getCoreImgMaxSize()
            f.seek(0)
            f.write(bootBuf)
            f.write(coreBuf)
            for i in range(0, cls._getCoreBufMaxSize() - len(coreBuf) - len(bootBuf)):
                f.write(b'\x00')

        # fill custom attributes
        platform_install_info.mbr_installed = True
        platform_install_info.allow_floppy = bAllowFloppy
        platform_install_info.bpb = bBpb
        platform_install_info.rs_codes = bAddRsCodes

    @classmethod
    def remove_from_mbr(cls, platform_type, dev):
        cls._checkDisk(dev, None)

        with open(dev, "rb+") as f:
            # prepare allZeroBootBuf
            tmpBootBuf = f.read(Grub.DISK_SECTOR_SIZE)
            allZeroBootBuf = cls._getAllZeroBootBuf(tmpBootBuf)

            # write up to cls._getCoreImgMaxSize()
            f.seek(0)
            f.write(allZeroBootBuf)
            for i in range(0, cls._getCoreBufMaxSize() - len(allZeroBootBuf)):
                f.write(b'\x00')

    @staticmethod
    def check_rest_files(platform_type, source, bootDir, rest_files):
        srcFile = os.path.join(source.get_platform_directory(platform_type), "boot.img")
        assert os.path.exists(srcFile)

        dstFile = os.path.join(bootDir, "grub", platform_type.value, "boot.img")
        if os.path.exists(dstFile):
            assert dstFile in rest_files
            rest_files.remove(dstFile)
            if not compare_files(srcFile, dstFile):
                raise CompareWithSourceError("%s and %s are different" % (srcFile, dstFile))
        else:
            raise CompareWithSourceError("%s does not exist" % (dstFile))

        if len(rest_files) > 0:
            raise CompareWithSourceError("redundant file %s found" % (rest_files[0]))

    @staticmethod
    def _getCoreBufMaxSize():
        return Grub.DISK_SECTOR_SIZE * 1024

    @staticmethod
    def _getCoreBufPossibleSize(coreBuf):
        return (len(coreBuf) + Grub.DISK_SECTOR_SIZE - 1) // Grub.DISK_SECTOR_SIZE * Grub.DISK_SECTOR_SIZE * 2

    @classmethod
    def _checkDisk(cls, dev, exceptionClass):
        if not PartiUtil.isDiskOrParti(dev):
            if exceptionClass is not None:
                raise exceptionClass("'%s' must be a disk" % (dev))
            else:
                assert False

        pDev = parted.getDevice(dev)
        pDisk = parted.newDisk(pDev)
        if pDisk.type != "msdos":
            if exceptionClass is not None:
                raise exceptionClass("'%s' must have a MBR partition table" % (dev))
            else:
                assert False
        pPartiList = pDisk.getPrimaryPartitions()
        if len(pPartiList) == 0:
            if exceptionClass is not None:
                raise exceptionClass("'%s' have no partition" % (dev))
            else:
                assert False
        if pPartiList[0].geometry.start * pDev.sectorSize < cls._getCoreBufMaxSize():
            if exceptionClass is not None:
                raise exceptionClass("'%s' has no MBR gap or its MBR gap is too small" % (dev))
            else:
                assert False

    @staticmethod
    def _checkAndReadBootImg(platform_type, bootDir, exceptionClass):
        bootImgFile = os.path.join(bootDir, "grub", platform_type.value, "boot.img")
        if not os.path.exists(bootImgFile):
            raise exceptionClass("'%s' does not exist" % (bootImgFile))
        bootBuf = pathlib.Path(bootImgFile).read_bytes()
        if len(bootBuf) != Grub.DISK_SECTOR_SIZE:
            raise exceptionClass("the size of '%s' is not %u" % (bootImgFile, Grub.DISK_SECTOR_SIZE))
        return bootBuf

    @classmethod
    def _checkAndReadCoreImg(cls, platform_type, bootDir, exceptionClass):
        coreImgFile = os.path.join(bootDir, "grub", platform_type.value, Grub.getCoreImgNameAndTarget(platform_type)[0])
        if not os.path.exists(coreImgFile):
            raise exceptionClass("'%s' does not exist" % (coreImgFile))
        coreBuf = pathlib.Path(coreImgFile).read_bytes()
        if not (Grub.DISK_SECTOR_SIZE <= cls._getCoreBufPossibleSize(coreBuf) <= cls._getCoreBufMaxSize()):
            raise exceptionClass("the size of '%s' is invalid" % (coreImgFile))
        return coreBuf

    @staticmethod
    def _getAllZeroBootBuf(onDiskBootBuf):
        allZeroBootBuf = bytearray(Grub.DISK_SECTOR_SIZE - 2) + b'\x55\xAA'

        # see comment in cls.install_into_mbr()
        s, e = Grub.BOOT_MACHINE_BPB_START, Grub.BOOT_MACHINE_BPB_END
        allZeroBootBuf[s:e] = onDiskBootBuf[s:e]

        # see comment in cls.install_into_mbr()
        s, e = Grub.BOOT_MACHINE_WINDOWS_NT_MAGIC, Grub.BOOT_MACHINE_PART_END
        allZeroBootBuf[s:e] = onDiskBootBuf[s:e]

        return bytes(allZeroBootBuf)

    @classmethod
    def _getRsEncodedCoreBuf(cls, coreBuf, bigOrLittleEndian):
        noRsLen = struct.unpack_from(">H" if bigOrLittleEndian else "<H",
                                     coreBuf, Grub.DISK_SECTOR_SIZE + Grub.KERNEL_I386_PC_NO_REED_SOLOMON_LENGTH)[0]
        if noRsLen == 0xFFFF:
            raise InstallError("core.img version mismatch")

        newLen = cls._getCoreBufPossibleSize(coreBuf)
        coreBuf = bytearray(coreBuf)
        struct.pack_into(">I" if bigOrLittleEndian else "<I",
                         coreBuf, Grub.DISK_SECTOR_SIZE + Grub.KERNEL_I386_PC_REED_SOLOMON_REDUNDANCY, newLen)

        noRsLen += Grub.DISK_SECTOR_SIZE
        rsc = reedsolo.RSCodec(newLen - len(coreBuf))
        return bytes(coreBuf[:noRsLen]) + rsc.encode(coreBuf[noRsLen:])


class _Efi:

    """We only support removable, and not upgrading NVRAM"""

    @staticmethod
    def fill_platform_install_info(platform_type, platform_install_info, target_type, bootDir):
        efiDir = os.path.join(bootDir, "EFI")
        coreFullfn = os.path.join(bootDir, "grub", platform_type.value, Grub.getCoreImgNameAndTarget(platform_type)[0])
        efiFullfn = os.path.join(efiDir, "BOOT", Handy.getStandardEfiFilename(platform_type))

        if not os.path.exists(coreFullfn):
            raise TargetError("%s does not exist" % (coreFullfn))
        if not os.path.exists(efiFullfn):
            raise TargetError("%s does not exist" % (efiFullfn))
        if not compare_files(coreFullfn, efiFullfn):
            raise TargetError("%s and %s are different" % (coreFullfn, efiFullfn))

        platform_install_info.removable = True
        platform_install_info.nvram = False

    @staticmethod
    def install_info_efi_dir(platform_type, platform_install_info, bootDir, bRemovable, bUpdateNvram):
        assert bRemovable and not bUpdateNvram          # FIXME

        grubPlatDir = os.path.join(bootDir, "grub", platform_type.value)
        efiDir = os.path.join(bootDir, "EFI")
        efiDirLv2 = os.path.join(efiDir, "BOOT")
        efiFn = Handy.getStandardEfiFilename(platform_type)

        # create efi dir
        force_mkdir(efiDir)

        # create level 2 efi dir
        force_mkdir(efiDirLv2)

        # copy efi file
        coreName = Grub.getCoreImgNameAndTarget(platform_type)[0]
        shutil_copy_robust(os.path.join(grubPlatDir, coreName), os.path.join(efiDirLv2, efiFn))

        # fill custom attributes
        platform_install_info.removable = bRemovable
        platform_install_info.nvram = bUpdateNvram

    @staticmethod
    def remove_from_efi_dir(platform_type, bootDir):
        efiFn = Handy.getStandardEfiFilename(platform_type)
        for efiDir in [os.path.join(bootDir, "EFI")]:
            efiDirLv2 = os.path.join(efiDir, "BOOT")
            force_rm(os.path.join(efiDirLv2, efiFn))
            rmdir_if_empty(efiDirLv2)
            rmdir_if_empty(efiDir)

    @staticmethod
    def remove_remaining_crufts(bootDir):
        force_rm(os.path.join(bootDir, "EFI"))


class _PyCdLib:

    @staticmethod
    def init_platforms(p):
        pass


def _newNotValidPlatformInstallInfo(reason):
    ret = PlatformInstallInfo()
    ret.status = PlatformInstallInfo.Status.NOT_VALID
    ret.reason = reason
    return ret


def _newNotInstalledPlatformInstallInfo():
    ret = PlatformInstallInfo()
    ret.status = PlatformInstallInfo.Status.NOT_INSTALLED
    return ret


#     @staticmethod
#     def install_platform_for_iso(platform_type, source, bootDir, dev, bHddOrFloppy, bInstallMbr):

#         char *output = grub_util_path_concat (3, boot_grub, "i386-pc", "eltorito.img");
#       load_cfg = grub_util_make_temporary_file ();

#       grub_install_push_module ("biosdisk");
#       grub_install_push_module ("iso9660");
#       grub_install_make_image_wrap (source_dirs[GRUB_INSTALL_PLATFORM_I386_PC],
#             "/boot/grub", output,
#             0, load_cfg,
#             "i386-pc-eltorito", 0);
#       xorriso_push ("-boot-load-size");
#       xorriso_push ("4");
#       xorriso_push ("-boot-info-table");

# 	      char *boot_hybrid = grub_util_path_concat (2, source_dirs[GRUB_INSTALL_PLATFORM_I386_PC],
#             	 "boot_hybrid.img");
# 	      xorriso_push ("--grub2-boot-info");
# 	      xorriso_push ("--grub2-mbr");
# 	      xorriso_push (boot_hybrid);

#   /** build multiboot core.img */
#   grub_install_push_module ("pata");
#   grub_install_push_module ("ahci");
#   grub_install_push_module ("at_keyboard");
#   make_image (GRUB_INSTALL_PLATFORM_I386_MULTIBOOT, "i386-multiboot", "i386-multiboot/core.elf");
#   grub_install_pop_module ();
#   grub_install_pop_module ();
#   grub_install_pop_module ();
#   make_image_fwdisk (GRUB_INSTALL_PLATFORM_I386_IEEE1275, "i386-ieee1275", "ofwx86.elf");

#   grub_install_push_module ("part_apple");
#   make_image_fwdisk (GRUB_INSTALL_PLATFORM_POWERPC_IEEE1275, "powerpc-ieee1275", "powerpc-ieee1275/core.elf");
#   grub_install_pop_module ();

#   make_image_fwdisk (GRUB_INSTALL_PLATFORM_SPARC64_IEEE1275,
#          "sparc64-ieee1275-cdcore", "sparc64-ieee1275/core.img");

# self.pubkey = XXX         # --pubkey=FILE
# self.compress = XXX       # --compress=no|xz|gz|lzo

# ia64-efi

# mips-arc
# mips-qemu_mips-flash
# mips-qemu_mips-elf

# mipsel-arc
# mipsel-fuloong2f-flash
# mipsel-loongson
# mipsel-loongson-elf
# mipsel-qemu_mips-elf
# mipsel-qemu_mips-flash
# mipsel-yeeloong-flash

# powerpc-ieee1275

# riscv32-efi

# riscv64-efi

# sparc64-ieee1275-raw
# sparc64-ieee1275-cdcore
# sparc64-ieee1275-aout
