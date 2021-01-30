#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import lxml.etree
from ps_util import PsUtil
from ps_param import PsConst


class PsPluginManager:

    def __init__(self, param):
        self.param = param
        self.pluginDict = dict()

    def getPluginNameList(self):
        ret = os.listdir(PsConst.pluginsDir)
        ret = [x for x in ret if os.path.isdir(os.path.join(PsConst.pluginsDir, x))]
        return ret

    def getPlugin(self, pluginName):
        if pluginName not in self.pluginDict:
            mod = __import__("plugins.%s" % (pluginName))
            mod = getattr(mod, pluginName)
            self.pluginDict[pluginName] = PsPlugin(self.param, pluginName, os.path.join(PsConst.pluginsDir, pluginName), mod)
        return self.pluginDict[pluginName]


class PsPlugin:

    def __init__(self, param, pluginName, pluginDir, mod):
        self._mod = mod

    def start(self, serverId, serverDomainName, serverDataDir):
        tmpDir = os.path.join(PsConst.tmpDir, serverId)
        PsUtil.ensureDir(tmpDir)

        tmpWebRootDir = os.path.join(PsConst.tmpWebRootDir, serverId)
        PsUtil.ensureDir(tmpWebRootDir)

        pluginRuntimeData = {
            "server-id": serverId,
            "module-data": None,
        }

        argument = {
            "server-id": serverId,
            "domain-name": serverDomainName,
            "data-directory": serverDataDir,
            "temp-directory": tmpDir,
            "webroot-directory": tmpWebRootDir,
        }
        apacheCfg, pluginRuntimeData["module-data"] = self._mod.start(argument)
        return (apacheCfg, pluginRuntimeData)

    def stop(self, pluginRuntimeData):
        self._mod.stop(pluginRuntimeData["module-data"])

        tmpWebRootDir = os.path.join(PsConst.tmpWebRootDir, pluginRuntimeData["server-id"])
        PsUtil.forceDelete(tmpWebRootDir)

        tmpDir = os.path.join(PsConst.tmpDir, pluginRuntimeData["server-id"])
        PsUtil.forceDelete(tmpDir)
