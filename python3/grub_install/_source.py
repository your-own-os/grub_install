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
from ._util import rel_path, compare_files, compare_directories
from ._const import PlatformType
from ._errors import SourceError, CopySourceError


class Source:

    CAP_NLS = 1
    CAP_FONTS = 2
    CAP_THEMES = 3

    def __init__(self, base_dir=None):
        if base_dir is not None:
            self._baseDir = base_dir
        else:
            self._baseDir = "/"
        self._libDir = os.path.join(self._baseDir, "usr", "lib", "grub")
        self._shareDir = os.path.join(self._baseDir, "usr", "share", "grub")
        self._localeDir = os.path.join(self._baseDir, "usr", "share", "locale")
        self._themesDir = os.path.join(self._baseDir, "usr", "share", "grub", "themes")

        # check
        if not os.path.isdir(self._libDir):
            raise SourceError("directory %s does not exist" % (self._libDir))
        if not os.path.isdir(self._shareDir):
            raise SourceError("directory %s does not exist" % (self._shareDir))
        self.get_all_platform_directories()

    def supports(self, key):
        if key == self.CAP_NLS:
            return os.path.exists(self._localeDir)
        elif key == self.CAP_FONTS:
            return len(glob.glob(os.path.join(self._shareDir, "*.pf2"))) > 0
        elif key == self.CAP_THEMES:
            return os.path.exists(self._themesDir)
        else:
            assert False

    def get_all_platform_directories(self):
        ret = dict()
        for fullfn in glob.glob(os.path.join(self._libDir, "*")):
            n = os.path.basename(fullfn)
            try:
                ret[PlatformType(n)] = fullfn
            except ValueError:
                raise SourceError("invalid platform directory %s" % (fullfn))
        return ret

    def get_platform_directory(self, platform_type):
        ret = self.try_get_platform_directory(platform_type)
        assert ret is not None
        return ret

    def try_get_platform_directory(self, platform_type):
        assert isinstance(platform_type, PlatformType)
        ret = os.path.join(self._libDir, platform_type.value)
        if os.path.exists(ret):
            assert os.path.isdir(ret)
            return ret
        else:
            return None

    def get_all_locale_files(self):
        assert self.supports(self.CAP_NLS)
        ret = dict()
        for fullfn in glob.glob(os.path.join(self._localeDir, "**/LC_MESSAGES/grub.mo")):
            n = rel_path(self._localeDir, fullfn).split("/")[0]
            ret[n] = fullfn
        return ret

    def get_locale_file(self, locale_name):
        ret = self.try_get_locale_file(locale_name)
        assert ret is not None
        return ret

    def try_get_locale_file(self, locale_name):
        assert self.supports(self.CAP_NLS)
        ret = os.path.join(self._localeDir, locale_name, "LC_MESSAGES", "grub.mo")
        if os.path.exists(ret):
            assert os.path.isfile(ret)
            return ret
        else:
            return None

    def get_all_font_files(self):
        assert self.supports(self.CAP_FONTS)
        ret = dict()
        for fullfn in glob.glob(os.path.join(self._shareDir, "*.pf2")):
            n = os.path.basename(fullfn).replace(".pf2", "")
            ret[n] = fullfn
        return ret

    def get_font_file(self, font_name):
        ret = self.try_get_font_file(font_name)
        assert ret is not None
        return ret

    def try_get_font_file(self, font_name):
        assert self.supports(self.CAP_FONTS)
        ret = os.path.join(self._shareDir, font_name + ".pf2")
        if os.path.exists(ret):
            assert os.path.isfile(ret)
            return ret
        else:
            return None

    def get_default_font(self):
        assert self.supports(self.CAP_FONTS)
        return "unicode"

    def get_all_theme_directories(self):
        assert self.supports(self.CAP_THEMES)
        ret = dict()
        for fullfn in glob.glob(os.path.join(self._themesDir, "*")):
            n = os.path.basename(fullfn)
            ret[n] = fullfn
        return ret

    def get_theme_directory(self, theme_name):
        ret = self.try_get_theme_directory(theme_name)
        assert ret is not None
        return ret

    def try_get_theme_directory(self, theme_name):
        assert self.supports(self.CAP_THEMES)
        ret = os.path.join(self._themesDir, theme_name)
        if os.path.exists(ret):
            assert os.path.isdir(ret)
            return ret
        else:
            return None

    def get_default_theme(self):
        assert self.supports(self.CAP_THEMES)
        return "starfield"

    def copy_into(self, dest_dir):
        assert os.path.isdir(dest_dir)

        # copy platform directories
        tdir = os.path.join(dest_dir, rel_path(self._baseDir, self._libDir))
        os.makedirs(tdir, exist_ok=True)
        for fullfn in self.get_all_platform_directories().values():
            fullfn2 = os.path.join(tdir, rel_path(self._libDir, fullfn))
            if os.path.exists(fullfn2):
                if not compare_directories(fullfn, fullfn2):
                    raise CopySourceError("%s and %s are different" % (fullfn, fullfn2))
            else:
                shutil.copytree(fullfn, fullfn2)

        # copy locale files
        if self.supports(self.CAP_NLS):
            tdir = os.path.join(dest_dir, rel_path(self._baseDir, self._localeDir))
            os.makedirs(tdir, exist_ok=True)
            for fullfn in self.get_all_locale_files().values():
                fullfn2 = os.path.join(tdir, rel_path(self._localeDir, fullfn))
                if os.path.exists(fullfn2):
                    if not compare_files(fullfn, fullfn2):
                        raise CopySourceError("%s and %s are different" % (fullfn, fullfn2))
                else:
                    os.makedirs(os.path.dirname(fullfn2), exist_ok=True)
                    shutil.copy(fullfn, fullfn2)

        # copy font files
        if self.supports(self.CAP_FONTS):
            tdir = os.path.join(dest_dir, rel_path(self._baseDir, self._shareDir))
            os.makedirs(tdir, exist_ok=True)
            for fullfn in self.get_all_font_files().values():
                fullfn2 = os.path.join(tdir, rel_path(self._shareDir, fullfn))
                if os.path.exists(fullfn2):
                    if not compare_files(fullfn, fullfn2):
                        raise CopySourceError("%s and %s are different" % (fullfn, fullfn2))
                else:
                    shutil.copy(fullfn, fullfn2)

        # copy theme directories
        if self.supports(self.CAP_THEMES):
            tdir = os.path.join(dest_dir, rel_path(self._baseDir, self._themesDir))
            os.makedirs(tdir, exist_ok=True)
            for fullfn in self.get_all_theme_directories().values():
                fullfn2 = os.path.join(tdir, rel_path(self._themesDir, fullfn))
                if os.path.exists(fullfn2):
                    if not compare_directories(fullfn, fullfn2):
                        raise CopySourceError("%s and %s are different" % (fullfn, fullfn2))
                else:
                    shutil.copytree(fullfn, fullfn2)
