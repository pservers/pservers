
class _MultiInstanceFtpServer:

    def __init__(self, param):
        self.param = param

        self._dirDict = dict()      # <domain-name,file-directory>
        self._procDict = dict()     # <domain-name,process>

    def addFileDir(self, name, realPath):
        assert len(self._procDict) == 0
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def start(self):
        assert len(self._procDict) == 0

        # FIXME: we don't support allocate new ip and starts multiple servers
        if "fpemud-distfiles.local" in self._dirDict:
            tmpDict = dict()
            tmpDict["fpemud-distfiles.local"] = self._dirDict["fpemud-distfiles.local"]
        else:
            assert len(self._dirDict) == 1
            tmpDict = self._dirDict

        # for name, realPath in self._dirDict.items():
        for name, realPath in tmpDict.items():
            cfg = dict()
            cfg["logFile"] = os.path.join(PsConst.logDir, "ftp." + name + ".log")
            cfg["logMaxBytes"] = PsConst.updaterLogFileSize
            cfg["logBackupCount"] = PsConst.updaterLogFileCount
            cfg["ip"] = self.param.listenIp
            cfg["port"] = PsConst.ftpPort
            cfg["dir"] = realPath
            self._procDict[name] = subprocess.Popen([os.path.join(PsConst.libexecDir, "ftpd.py"), json.dumps(cfg)])
            PsUtil.waitSocketPortForProc("tcp", self.param.listenIp, PsConst.ftpPort, self._procDict[name])
            logging.info("Slave server \"ftp://%s\" started." % (name))

    def stop(self):
        for proc in self._procDict.values():
            PsUtil.procTerminate(proc, wait=True)
        self._procDict = dict()



class _MultiInstanceGitServer:

    def __init__(self, param):
        self.param = param

        self._dirDict = dict()      # <domain-name,repository-directory>
        self._procDict = dict()     # <domain-name,process>

    def addGitDir(self, name, realPath):
        assert len(self._procDict) == 0
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def start(self):
        assert len(self._procDict) == 0

        # FIXME: we don't support allocate new ip and starts multiple servers
        assert len(self._dirDict) == 1

        for name, realPath in self._dirDict.items():
            self._procDict[name] = subprocess.Popen([
                "/usr/libexec/git-core/git-daemon",
                "--export-all",
                "--listen=%s" % (self.param.listenIp),
                "--port=%d" % (PsConst.gitPort),
                "--base-path=%s" % (realPath),
            ])
            PsUtil.waitSocketPortForProc("tcp", self.param.listenIp, PsConst.gitPort, self._procDict[name])
            logging.info("Slave server \"git://%s\" started." % (name))

    def stop(self):
        for proc in self._procDict.values():
            PsUtil.procTerminate(proc, wait=True)
        self._procDict = dict()
