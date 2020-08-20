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
                    if self.httpServer is None:
                        self.httpServer = _HttpServer(self.param)
                    self.httpServer.addFileDir(serverObj.domainName, serverObj.dataDir)
                    continue
                if serverObj.serverType == "file" and advertiseType == "ftp":
                    if self.ftpServer is None:
                        self.ftpServer = _FtpServer(self.param)
                    self.ftpServer.addFileDir(serverObj.domainName, serverObj.dataDir)
                    continue
                if serverObj.serverType == "git" and advertiseType == "klaus":
                    if self.httpServer is None:
                        self.httpServer = _HttpServer(self.param)
                    self.httpServer.addGitDir(serverObj.domainName, serverObj.dataDir)
                    continue
                assert False

        # start servers
        if self.httpServer is not None:
            self.httpServer.start()
        if self.ftpServer is not None:
            self.ftpServer.start()

    def dispose(self):
        if self.ftpServer is not None:
            self.ftpServer.stop()
        if self.httpServer is not None:
            self.httpServer.stop()


class _HttpServer:

    def __init__(self, param):
        self.param = param
        self._cfgFn = os.path.join(PsConst.tmpDir, "httpd.conf")
        self._pidFile = os.path.join(PsConst.tmpDir, "httpd.pid")
        self._errorLogFile = os.path.join(PsConst.logDir, "httpd-error.log")
        self._accessLogFile = os.path.join(PsConst.logDir, "httpd-access.log")

        self._dirDict = dict()          # files
        self._gitDirDict = dict()       # git repositories

        self._proc = None

    def addFileDir(self, name, realPath):
        assert self._proc is not None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def addGitDir(self, name, realPath):
        assert self._proc is not None
        assert _checkNameAndRealPath(self._gitDirDict, name, realPath)
        self._gitDirDict[name] = realPath

    def start(self):
        assert self._proc is None
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/apache2", "-f", self._cfgFn, "-DFOREGROUND"])
        PsUtil.waitTcpServiceForProc(self.param.listenIp, self.param.httpPort, self._proc)
        logging.info("Slave server (http) started, listening on port %d." % (self.param.httpPort))

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None

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

        for name, realPath in self._dirDict.items():
            pass

        for name, realPath in self._gitDirDict.items():
            pass


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

        with open(self._cfgFn, "w") as f:
            f.write(buf)


class _FtpServer:

    def __init__(self, param):
        self.param = param
        self._cfgFn = os.path.join(PsConst.tmpDir, "ftpd.conf")
        self._pidFile = os.path.join(PsConst.tmpDir, "ftpd.pid")
        self._errorLogFile = os.path.join(PsConst.logDir, "ftpd-error.log")
        self._accessLogFile = os.path.join(PsConst.logDir, "ftpd-access.log")

        self._dirDict = dict()

        self._proc = None

    def addFileDir(self, name, realPath):
        assert self._proc is not None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def start(self):
        assert self._proc is None
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/proftpd", "-f", self._cfgFn, "-n"])
        PsUtil.waitTcpServiceForProc(self.param.listenIp, self.param.ftpPort, self._proc)
        logging.info("Slave server (ftp) started, listening on port %d." % (self.param.ftpPort))

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
        buf += 'AuthPAM off\n'
        buf += 'Port %d\n' % (self.param.ftpPort)
        buf += 'Umask 022\n'

        for name, realPath in self._dirDict.items():
            buf += 'DefaultRoot %s\n' % (self.)

            # # Generally files are overwritable.
            # AllowOverwrite on

            # # Disallow the use of the SITE CHMOD command.
            # <Limit SITE_CHMOD>
            # DenyAll
            # </Limit>

            # # A basic anonymous FTP account without an upload directory.
            # <Anonymous ~ftp>
            # User ftp
            # Group ftp

            # # Clients can login with the username "anonymous" and "ftp".
            # UserAlias anonymous ftp

            # # Limit the maximum number of parallel anonymous logins to 10.
            # MaxClients 10

            # # Prohibit the WRITE command for the anonymous users.
            # <Limit WRITE>
            #     DenyAll
            # </Limit>
            # </Anonymous>

        with open(self._cfgFn, "w") as f:
            f.write(buf)


def _checkNameAndRealPath(dictObj, name, realPath):
    if name in dictObj:
        return False
    if not os.path.isabs(realPath) or realPath.endswith("/"):
        return False
    if PsUtil.isPathOverlap(realPath, dictObj.values()):
        return False
    return True
