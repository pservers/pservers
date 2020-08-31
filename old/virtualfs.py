
class VirtualFS(pyftpdlib.filesystems.AbstractedFS):

    # --- Pathname / conversion utilities

    def validpath(self, path):
        if self._isVirtualRootDir(path):
            return True
        else:
            path = self._path2rpath(path)
            path = os.path.realpath(path)
            return self._rpathInRange(path)

    # --- Wrapper methods around open() and tempfile.mkstemp

    def open(self, filename, mode):
        return super().open(self._path2rpath(filename), mode)

    def mkstemp(self, suffix='', prefix='', dir=None, mode='wb'):
        raise NotImplementedError()

    # --- Wrapper methods around os.* calls

    def chdir(self, path):
        if self._isVirtualRootDir(path):
            os.chdir("/")                           # FIXME
        else:
            os.chdir(self._path2rpath(path))
        self.cwd = self.fs2ftp(path)

    def mkdir(self, path):
        raise NotImplementedError()

    def listdir(self, path):
        if self._isVirtualRootDir(path):
            return self._listVirtualRootDir()
        else:
            return super().listdir(self._path2rpath(path))

    def listdirinfo(self, path):
        raise NotImplementedError()

    def rmdir(self, path):
        raise NotImplementedError()

    def remove(self, path):
        raise NotImplementedError()

    def rename(self, src, dst):
        raise NotImplementedError()

    def chmod(self, path, mode):
        raise NotImplementedError()

    def stat(self, path):
        if self._isVirtualRootDir(path):
            return os.stat("/")                     # FIXME
        else:
            return super().stat(self._path2rpath(path))

    def utime(self, path, timeval):
        raise NotImplementedError()

    def lstat(self, path):
        if self._isVirtualRootDir(path):
            return os.lstat("/")                    # FIXME
        else:
            return super().lstat(self._path2rpath(path))

    def readlink(self, path):
        raise NotImplementedError()

    # --- Wrapper methods around os.path.* calls

    def isfile(self, path):
        if self._isVirtualRootDir(path) or self._isVirtualSiteDir(path):
            return False
        else:
            return super().isfile(self._path2rpath(path))

    def islink(self, path):
        if self._isVirtualRootDir(path) or self._isVirtualSiteDir(path):
            return False
        else:
            return super().islink(self._path2rpath(path))

    def isdir(self, path):
        if self._isVirtualRootDir(path) or self._isVirtualSiteDir(path):
            return True
        else:
            return super().isdir(self._path2rpath(path))

    def getsize(self, path):
        if self._isVirtualRootDir(path):
            return os.path.getsize("/")                         # FIXME
        elif self._isVirtualSiteDir(path):
            return super().getsize(self._path2rpath(path))     # FIXME
        else:
            return super().getsize(self._path2rpath(path))

    def getmtime(self, path):
        if self._isVirtualRootDir(path):
            return os.path.getmtime("/")                        # FIXME
        elif self._isVirtualSiteDir(path):
            return super().getmtime(self._path2rpath(path))    # FIXME
        else:
            return super().getmtime(self._path2rpath(path))

    def realpath(self, path):
        if self._isVirtualRootDir(path) or self._isVirtualSiteDir(path):
            return path
        else:
            path = self._path2rpath(path)
            path = os.path.realpath(path)
            path = self._rpath2path(path)
            return path

    def lexists(self, path):
        if self._isVirtualRootDir(path) or self._isVirtualSiteDir(path):
            return True
        else:
            return super().lexists(self._path2rpath(path))

    def get_user_by_uid(self, uid):
        return "owner"

    def get_group_by_gid(self, gid):
        return "group"

    def _isVirtualRootDir(self, path):
        assert os.path.isabs(path)
        return path == "/"

    def _isVirtualSiteDir(self, path):
        # "/xyz" are virtual site directories
        assert os.path.isabs(path) and not self._isVirtualRootDir(path)
        return path.count("/") == 1

    def _listVirtualRootDir(self):
        global cfg
        return sorted(cfg["dirmap"].keys())

    def _path2rpath(self, path):
        global cfg
        assert os.path.isabs(path) and not self._isVirtualRootDir(path)
        for prefix, realPath in cfg["dirmap"].items():
            if path == "/" + prefix:
                return realPath
            if path.startswith("/" + prefix + "/"):
                return path.replace("/" + prefix, realPath, 1)
        raise FileNotFoundError("No such file or directory: '%s'" % (path))

    def _rpath2path(self, rpath):
        global cfg
        for prefix, realPath in cfg["dirmap"].items():
            if rpath == realPath:
                return "/" + prefix
            if rpath.startswith(realPath + "/"):
                return rpath.replace(realPath, "/" + prefix, 1)
        assert False

    def _rpathInRange(self, rpath):
        global cfg
        for prefix, realPath in cfg["dirmap"].items():
            if rpath == realPath:
                return True
            if rpath.startswith(realPath + "/"):
                return True
        return False

