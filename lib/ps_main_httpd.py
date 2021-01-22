#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import subprocess
from ps_util import PsUtil
from ps_param import PsConst


class PsMainHttpServer:

    def __init__(self, param):
        self.param = param
        self._rootDir = os.path.join(PsConst.tmpDir, "httpd.root")
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
        self._generateFiles()
        self._generateCfgFn()
        self._proc = subprocess.Popen(["/usr/sbin/apache2", "-f", self._cfgFn, "-DFOREGROUND"])
        PsUtil.waitSocketPortForProc("tcp", self.param.listenIp, PsConst.httpPort, self._proc)

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None

    def _generateFiles(self):
        # virtual root directory
        PsUtil.ensureDir(self._rootDir)

        userInfo = ("write", "klaus", "write")      # (username, scope, password)
        for name, realPath in self._gitDirDict.items():
            # htdigest file
            htdigestFn = os.path.join(PsConst.tmpDir, "auth-%s.htdigest" % (name))
            PsUtil.generateApacheHtdigestFile(htdigestFn, [userInfo])

            # wsgi script
            wsgiFn = os.path.join(PsConst.tmpDir, "wsgi-%s.py" % (name))
            with open(wsgiFn, "w") as f:
                buf = ''
                buf += '#!/usr/bin/python3\n'
                buf += '# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-\n'
                buf += '\n'
                buf += 'from klaus.contrib.wsgi_autoreloading import make_autoreloading_app\n'
                buf += '\n'
                buf += 'application = make_autoreloading_app("%s", "%s",\n' % (realPath, name)
                buf += '                                     use_smarthttp=True,\n'
                buf += '                                     unauthenticated_push=True,\n'
                buf += '                                     htdigest_file=open("%s"))\n' % (htdigestFn)
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
        buf += "LoadModule wsgi_module            %s/mod_wsgi.so\n" % (modulesDir)
        # buf += "LoadModule env_module             %s/mod_env.so\n" % (modulesDir)
        buf += "\n"
        buf += 'PidFile "%s"\n' % (self._pidFile)
        buf += 'ErrorLog "%s"\n' % (self._errorLogFile)
        buf += r'LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" common' + "\n"
        buf += 'CustomLog "%s" common\n' % (self._accessLogFile)
        buf += "\n"
        buf += "Listen %d http\n" % (PsConst.httpPort)
        buf += "\n"
        buf += "ServerName none\n"                          # dummy value
        buf += 'DocumentRoot "%s"\n' % (self._rootDir)
        buf += '<Directory "%s">\n' % (self._rootDir)
        buf += '    Options Indexes\n'
        buf += '    Require all granted\n'
        buf += '</Directory>\n'
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

        for name, realPath in self._gitDirDict.items():
            buf += '<VirtualHost *>\n'
            buf += '    ServerName %s\n' % (name)
            buf += '    WSGIScriptAlias / %s\n' % (self._gitFilesDict[name][1])
            buf += '    WSGIChunkedRequest On\n'
            buf += '</VirtualHost>\n'
            buf += '\n'

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
