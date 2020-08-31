
class _FtpServer:

    def __init__(self, param):
        self.param = param
        self._cfgFn = os.path.join(PsConst.tmpDir, "ftpd.conf")
        self._pidFile = os.path.join(PsConst.tmpDir, "ftpd.pid")
        self._scoreBoardFile = os.path.join(PsConst.tmpDir, "ftpd.scoreboard")
        self._errorLogFile = os.path.join(PsConst.logDir, "ftpd-error.log")
        self._accessLogFile = os.path.join(PsConst.logDir, "ftpd-access.log")

        self._dirDict = dict()

        self._proc = None

    def addFileDir(self, name, realPath):
        assert self._proc is None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def start(self):
        assert self._proc is None
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/proftpd", "-c", self._cfgFn, "-n"])
        PsUtil.waitTcpServiceForProc(self.param.listenIp, PsConst.ftpPort, self._proc)
        logging.info("Server (ftp) started, listening on port %d." % (PsConst.ftpPort))

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None

    def _generateCfgFn(self):
        buf = ""
        buf += 'ServerName "ProFTPD Default Server"\n'
        buf += 'ServerType standalone\n'
        buf += 'DefaultServer on\n'
        buf += 'RequireValidShell off\n'
        buf += 'User %s\n' % (PsConst.user)
        buf += 'Group %s\n' % (PsConst.group)
        buf += 'AuthPAM off\n'
        buf += 'WtmpLog off\n'
        buf += 'Port %d\n' % (PsConst.ftpPort)
        buf += 'PidFile %s\n' % (self._pidFile)
        buf += 'ScoreboardFile %s\n' % (self._scoreBoardFile)
        buf += 'Umask 022\n'
        buf += '\n'

        # FIXME: very few ftp clients support rfc7151, so we can only have one VirtualHost
        if "fpemud-distfiles.local" in self._dirDict:
            tmpDict = dict()
            tmpDict["fpemud-distfiles.local"] = self._dirDict["fpemud-distfiles.local"]
        else:
            assert len(self._dirDict) == 1
            tmpDict = self._dirDict

        # for name, realPath in self._dirDict.items():
        for name, realPath in tmpDict.items():
            buf += '<VirtualHost %s>\n' % (name)
            buf += '    <Anonymous %s>\n' % (realPath)
            buf += '        User %s\n' % (PsConst.user)
            buf += '        Group %s\n' % (PsConst.group)
            buf += '        UserAlias anonymous %s\n' % (PsConst.user)
            buf += '        <Directory *>\n'
            buf += '            <Limit WRITE>\n'
            buf += '                DenyAll\n'
            buf += '            </Limit>\n'
            buf += '        </Directory>\n'
            buf += '    </Anonymous>\n'
            buf += '</VirtualHost>\n'
            buf += '\n'

        with open(self._cfgFn, "w") as f:
            f.write(buf)

