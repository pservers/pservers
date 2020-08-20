#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import json
import signal
import logging
import subprocess
from ps_util import PsUtil
from ps_param import PsConst


class PsSlaveServers:

    def __init__(self, param):
        self.param = param
        self.httpServer = None
        self.ftpServer = None

        # register servers by advertise type
        for serverObj in self.param.serverDict.values():
            for advertiseType in serverObj.advertiseTypeList:
                if serverObj.serverType == "file" and advertiseType == "http":
                    self.httpServer = True
                    continue
                if serverObj.serverType == "file" and advertiseType == "ftp":
                    self.ftpServer = True
                    continue
                if serverObj.serverType == "git" and advertiseType == "klaus":
                    self.httpServer = True
                    continue
                assert False

        # create servers
        if self.httpServer is not None:
            self.httpServer = _HttpServer(self.param)
            self.httpServer.start()
        if self.ftpServer is not None:
            self.ftpServer = _FtpServer(self.param)
            self.ftpServer.start()

    def dispose(self):
        if self.ftpServer is not None:
            self.ftpServer.stop()
        if self.httpServer is not None:
            self.httpServer.stop()


class _HttpServer:

    def __init__(self, param):
        self.param = param
        self._virtRootDir = os.path.join(PsConst.tmpDir, "vroot-httpd")
        self._cfgFn = os.path.join(PsConst.tmpDir, "httpd.conf")
        self._pidFile = os.path.join(PsConst.tmpDir, "httpd.pid")
        self._errorLogFile = os.path.join(PsConst.logDir, "httpd-error.log")
        self._accessLogFile = os.path.join(PsConst.logDir, "httpd-access.log")

        self._dirDict = dict()          # files
        self._gitDirDict = dict()       # git repositories

        self._proc = None

    def start(self):
        assert self._proc is None
        self._generateVirtualRootDir()
        self._generateVirtualRootDirFile()
        self._generateVirtualRootDirGit()
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/apache2", "-f", self._cfgFn, "-DFOREGROUND"])
        PsUtil.waitTcpServiceForProc(self.param.listenIp, self.param.httpPort, self._proc)
        logging.info("Slave server (http) started, listening on port %d." % (self.param.httpPort))

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None

    def addFileDir(self, name, realPath):
        assert self._proc is not None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath
        self._generateVirtualRootDirFile()
        self._generateCfgFn()
        os.kill(self._proc.pid, signal.SIGUSR1)

    def addGitDir(self, name, realPath):
        assert self._proc is not None
        assert _checkNameAndRealPath(self._gitDirDict, name, realPath)
        self._gitDirDict[name] = realPath
        self._generateVirtualRootDirGit()
        self._generateCfgFn()
        os.kill(self._proc.pid, signal.SIGUSR1)

    def _generateVirtualRootDir(self):
        PsUtil.ensureDir(self._virtRootDir)

    def _generateVirtualRootDirFile(self):
        if len(self._dirDict) == 0:
            return

        virtRootDirFile = os.path.join(self._virtRootDir, "file")

        PsUtil.ensureDir(virtRootDirFile)

        # create new directories
        for name, realPath in self._dirDict.items():
            dn = os.path.join(virtRootDirFile, name)
            if not os.path.exists(dn):
                os.symlink(realPath, dn)

        # remove old directories
        for dn in os.listdir(virtRootDirFile):
            if dn not in self._dirDict:
                os.unlink(dn)

    def _generateVirtualRootDirGit(self):
        if len(self._gitDirDict) == 0:
            return

        virtRootDirGit = os.path.join(self._virtRootDir, "git")
        PsUtil.ensureDir(virtRootDirGit)

        # create new directories
        for name, realPath in self._gitDirDict.items():
            dn = os.path.join(virtRootDirGit, name)
            if not os.path.exists(dn):
                os.symlink(realPath, dn)

        # remove old directories
        for dn in os.listdir(virtRootDirGit):
            if dn not in self._gitDirDict:
                os.unlink(dn)

    def _generateCfgFn(self):
        modulesDir = "/usr/lib64/apache2/modules"
        buf = ""

        # modules
        buf += "LoadModule log_config_module      %s/mod_log_config.so\n" % (modulesDir)
        buf += "LoadModule unixd_module           %s/mod_unixd.so\n" % (modulesDir)
        buf += "LoadModule alias_module           %s/mod_alias.so\n" % (modulesDir)
        buf += "LoadModule authz_core_module      %s/mod_authz_core.so\n" % (modulesDir)            # it's strange why we need this module and Require directive since we have no auth at all
        buf += "LoadModule autoindex_module       %s/mod_autoindex.so\n" % (modulesDir)
        # buf += "LoadModule env_module             %s/mod_env.so\n" % (modulesDir)
        # buf += "LoadModule cgi_module             %s/mod_cgi.so\n" % (modulesDir)
        buf += "\n"

        # global settings
        buf += 'PidFile "%s"\n' % (self._pidFile)
        buf += 'ErrorLog "%s"\n' % (self._errorLogFile)
        buf += r'LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" common' + "\n"
        buf += 'CustomLog "%s" common\n' % (self._accessLogFile)
        buf += "\n"
        buf += "Listen %d http\n" % (self.param.httpPort)
        buf += "ServerName none\n"                              # dummy value
        buf += "\n"
        buf += 'DocumentRoot "%s"\n' % (self._virtRootDir)
        buf += '<Directory "%s">\n' % (self._virtRootDir)
        buf += '  Options Indexes FollowSymLinks\n'
        buf += '  Require all denied\n'
        buf += '</Directory>\n'
        if len(self._dirDict) > 0:
            buf += '<Directory "%s">\n' % (os.path.join(self._virtRootDir, "file"))
            buf += '  Require all granted\n'
            buf += '</Directory>\n'
        buf += "\n"

        # git settings
        if len(self._gitDirDict) > 0:
            # buf += "SetEnv GIT_PROJECT_ROOT \"${REPO_ROOT_DIR}\""
            # buf += "SetEnv GIT_HTTP_EXPORT_ALL"
            # buf += ""
            # buf += "  AliasMatch ^/(.*/objects/[0-9a-f]{2}/[0-9a-f]{38})$          \"${REPO_ROOT_DIR}/\$1\""
            # buf += "  AliasMatch ^/(.*/objects/pack/pack-[0-9a-f]{40}.(pack|idx))$ \"${REPO_ROOT_DIR}/\$1\""
            # buf += ""
            # buf += "  ScriptAlias / /usr/libexec/git-core/git-http-backend/"
            # buf += ""
            # buf += "  <Directory \"${REPO_ROOT_DIR}\">"
            # buf += "    AllowOverride None"
            # buf += "  </Directory>"
            buf += "\n"

        # write file atomically
        with open(self._cfgFn + ".tmp", "w") as f:
            f.write(buf)
        os.rename(self._cfgFn + ".tmp", self._cfgFn)


class _FtpServer:

    def __init__(self, param):
        self.param = param
        self._execFile = os.path.join(PsConst.libexecDir, "ftpd.py")
        self._cfgFile = os.path.join(PsConst.tmpDir, "ftpd.cfg")
        self._logFile = os.path.join(PsConst.logDir, "ftpd.log")

        self._dirDict = dict()

        self._proc = None

    def start(self):
        assert self._proc is None
        self._generateCfgFile()
        self._proc = subprocess.Popen([self._execFile, self._cfgFile], cwd=PsConst.cacheDir)
        PsUtil.waitTcpServiceForProc(self.param.listenIp, self.param.ftpPort, self._proc)
        logging.info("Slave server (ftp) started, listening on port %d." % (self.param.ftpPort))

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None

    def addFileDir(self, name, realPath):
        assert self._proc is not None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath
        self._generateCfgFile()
        os.kill(self._proc.pid, signal.SIGUSR1)

    def _generateCfgFile(self):
        # generate file content
        dataObj = dict()
        dataObj["logFile"] = self._logFile
        dataObj["logMaxBytes"] = PsConst.updaterLogFileSize
        dataObj["logBackupCount"] = PsConst.updaterLogFileCount
        dataObj["ip"] = self.param.listenIp
        dataObj["port"] = self.param.ftpPort
        dataObj["dirmap"] = self._dirDict

        # write file atomically
        with open(self._cfgFile + ".tmp", "w") as f:
            json.dump(dataObj, f)
        os.rename(self._cfgFile + ".tmp", self._cfgFile)


def _checkNameAndRealPath(dictObj, name, realPath):
    if name in dictObj:
        return False
    if not os.path.isabs(realPath) or realPath.endswith("/"):
        return False
    if PsUtil.isPathOverlap(realPath, dictObj.values()):
        return False
    return True
