#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import signal
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

        self._cfgDict = dict()      # <cfg-id,cfg>
        self._proc = None

    def addConfig(self, cfgId, cfg):
        assert cfgId not in self._cfgDict
        self._cfgDict[cfgId] = cfg
        self._refresh()

    def updateConfig(self, cfgId, cfg):
        self._cfgDict[cfgId] = cfg
        self._refresh()

    def removeConfig(self, cfgId):
        del self._cfgDict[cfgId]
        self._refresh()

    def batchRemoveConfig(self, cfgIdList):
        for cfgId in cfgIdList:
            del self._cfgDict[cfgId]
        self._refresh()

    def start(self):
        assert self._proc is None
        self._generateCfgFn()
        PsUtil.ensureDir(self._rootDir)
        self._proc = subprocess.Popen(["/usr/sbin/apache2", "-f", self._cfgFn, "-DFOREGROUND"])
        PsUtil.waitSocketPortForProc("tcp", self.param.listenIp, PsConst.httpPort, self._proc)

    def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None
        PsUtil.forceDelete(self._rootDir)

    def _generateCfgFn(self):
        modulesDir = "/usr/lib64/apache2/modules"

        moduleDict = {
            "log_config_module": "mod_log_config.so",
            "unixd_module": "mod_unixd.so",
            "alias_module": "mod_alias.so",
            "authz_core_module": "mod_authz_core.so",       # it's strange why we need this module and Require directive since we have no auth at all
            "autoindex_module": "mod_autoindex.so",
        }
        for cfg in self._cfgDict.values():
            for k, v in cfg["module-dependencies"].items():
                if k not in moduleDict:
                    moduleDict[k] = v
                else:
                    assert moduleDict[k] == v

        buf = ""
        for k, v in moduleDict.items():
            buf += "LoadModule %s %s\n" % (k, os.path.join(modulesDir, v))
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
        for cfg in self._cfgDict.values():
            buf += '<VirtualHost *>\n'
            buf += "    " + cfg["config-segment"].replace("\n", "\n    ")           # FIXME: add indent for every line
            buf += '</VirtualHost>\n'
            buf += "\n"
        with open(self._cfgFn, "w") as f:
            f.write(buf)

    def _refresh(self):
        if self._proc is not None:
            self._generateCfgFn()
            os.kill(self._proc.pid, signal.SIGUSR1)


def _checkNameAndRealPath(dictObj, name, realPath):
    if name in dictObj:
        return False
    if not os.path.isabs(realPath) or realPath.endswith("/"):
        return False
    if PsUtil.isPathOverlap(realPath, dictObj.values()):
        return False
    return True
