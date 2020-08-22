#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
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
        # if self.ftpServer is not None:
        #     self.ftpServer.start()

    def dispose(self):
        # if self.ftpServer is not None:
        #     self.ftpServer.stop()
        if self.httpServer is not None:
            self.httpServer.stop()


class _HttpServer:

    def __init__(self, param):
        self.param = param
        self._cfgFn = os.path.join(PsConst.tmpDir, "httpd.conf")
        self._pidFile = os.path.join(PsConst.tmpDir, "httpd.pid")
        self._errorLogFile = os.path.join(PsConst.logDir, "httpd-error.log")
        self._accessLogFile = os.path.join(PsConst.logDir, "httpd-access.log")

        # file
        self._dirDict = dict()          # <domain-name,file-directory>

        # git
        self._gitDirDict = dict()       # <domain-name,git-repositories-directory>
        self._gitFilesDict = dict()     # <domain-name,(wsgi-script-filename,htdigest-filename)

        self._proc = None

    def addFileDir(self, name, realPath):
        assert self._proc is None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def addGitDir(self, name, realPath):
        assert self._proc is None
        assert _checkNameAndRealPath(self._gitDirDict, name, realPath)
        self._gitDirDict[name] = realPath
        self._gitFilesDict[name] = None

    def start(self):
        assert self._proc is None
        self._generateKlausFiles()
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/apache2", "-f", self._cfgFn, "-DFOREGROUND"])
        PsUtil.waitTcpServiceForProc(self.param.listenIp, PsConst.httpPort, self._proc)
        logging.info("Server (http) started, listening on port %d." % (PsConst.httpPort))

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None

    def _generateKlausFiles(self):
        userInfo = ("write", "klaus", "write")      # (username, scope, password)
        for name, realPath in self._gitDirDict.items():
            # htdigest file
            htdigestFn = os.path.join(PsConst.tmpDir, "auth-%s.htdigest" % (name))
            PsUtil.generateApacheHtdigestFile(htdigestFn, [userInfo])

            # wsgi script
            wsgiFn = os.path.join(PsConst.tmpDir, "wsgi-%s.py" % (name))
            with open(wsgiFn, "w") as f:
                buf = ''
                buf += 'from klaus.contrib.wsgi_autoreloading import make_autoreloading_app\n'
                buf += '\n'
                buf += 'app = make_autoreloading_app("%s", "%s",\n' % (realPath, name)
                buf += '                             use_smarthttp=True,\n'
                buf += '                             unauthenticated_push=True,\n'
                buf += '                             htdigest_file=open("%s"))\n' % (htdigestFn)
                f.write(buf)

            self._gitFilesDict[name] = (htdigestFn, wsgiFn)

    def _generateCfgFn(self):
        modulesDir = "/usr/lib64/apache2/modules"
        buf = ""

        buf += "LoadModule log_config_module      %s/mod_log_config.so\n" % (modulesDir)
        buf += "LoadModule unixd_module           %s/mod_unixd.so\n" % (modulesDir)
        buf += "LoadModule alias_module           %s/mod_alias.so\n" % (modulesDir)
        buf += "LoadModule authz_core_module      %s/mod_authz_core.so\n" % (modulesDir)            # it's strange why we need this module and Require directive since we have no auth at all
        buf += "LoadModule autoindex_module       %s/mod_autoindex.so\n" % (modulesDir)
        # buf += "LoadModule env_module             %s/mod_env.so\n" % (modulesDir)
        # buf += "LoadModule cgi_module             %s/mod_cgi.so\n" % (modulesDir)
        buf += "\n"
        buf += 'PidFile "%s"\n' % (self._pidFile)
        buf += 'ErrorLog "%s"\n' % (self._errorLogFile)
        buf += r'LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" common' + "\n"
        buf += 'CustomLog "%s" common\n' % (self._accessLogFile)
        buf += "\n"
        buf += "ServerName none\n"                          # dummy value
        buf += "Listen %d http\n" % (PsConst.httpPort)
        buf += "\n"

        for name, realPath in self._dirDict.items():
            buf += '<VirtualHost *>\n'
            buf += '    ServerName %s\n' % (name)
            buf += '    DocumentRoot "%s"\n' % (realPath)
            buf += '    <Directory "%s">\n' % (realPath)
            buf += '        Options Indexes\n'
            buf += '        Require all granted\n'
            buf += '    </Directory>\n'
            buf += '</VirtualHost>\n'
            buf += '\n'

        # for name, realPath in self._gitDirDict.items():
        #     buf += '<VirtualHost *>\n'
        #     buf += '    ServerName %s\n' % (name)
        #     buf += '    WSGIScriptAlias / %s\n' % (self._gitFilesDict[name][1])
        #     buf += '    WSGIDaemonProcess\n'
        #     buf += '    WSGIProcessGroup \n'
        #     buf += '</VirtualHost>\n'
        #     buf += '\n'

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
        assert self._proc is None
        assert _checkNameAndRealPath(self._dirDict, name, realPath)
        self._dirDict[name] = realPath

    def start(self):
        assert self._proc is None
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/proftpd", "-f", self._cfgFn, "-n"])
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
        buf += 'AuthPAM off\n'
        buf += 'Port %d\n' % (PsConst.ftpPort)
        buf += 'Umask 022\n'

        for name, realPath in self._dirDict.items():
            buf += 'DefaultRoot %s\n' % (realPath)

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
