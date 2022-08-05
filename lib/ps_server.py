#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import glob
import json
from ps_util import PsUtil
from ps_param import PsConst


class PsServerManager:

    def __init__(self, param):
        self.param = param

    def loadServers(self):
        for fn in glob.glob(os.path.join(PsConst.etcDir, "*.server")):
            serverId = PsUtil.rreplace(os.path.basename(fn), ".server", "", 1)
            self.param.serverDict[serverId] = PsServer(self.param, serverId, fn)


class PsServer:

    def __init__(self, param, serverId, serverFile):
        self.param = param

        with open(serverFile, "r") as f:
            cfgDict = json.load(f)

        # server id
        self.id = serverId

        # data directory
        self.dataDir = os.path.join(PsConst.varDir, self.id)
        PsUtil.ensureDir(self.dataDir)

        # domain name
        self.domainName = cfgDict["domain-name"]
        if not self.domainName.endswith(".private"):
            raise Exception("server %s: invalid domain-name %s" % (self.id, self.domainName))
        self.domainName = self.domainName.replace(".private", ".local")                             # FIXME
        del cfgDict["domain-name"]

        # server type
        self.serverType = cfgDict["server-type"]
        if self.serverType not in self.param.pluginManager.getPluginNameList():
            raise Exception("server %s: invalid server type %s" % (self.id, self.serverType))
        del cfgDict["server-type"]

        # cfgDict
        self.cfgDict = cfgDict

        # pluginRuntimeData
        self.pluginRuntimeData = None

    def startAndGetMainHttpServerConfig(self):
        pluginObj = self.param.pluginManager.getPlugin(self.serverType)
        cfg, self.pluginRuntimeData = pluginObj.start(self.id, self.domainName, self.dataDir)
        return cfg

    def stop(self):
        if self.pluginRuntimeData is not None:
            pluginObj = self.param.pluginManager.getPlugin(self.serverType)
            pluginObj.stop(self.pluginRuntimeData)
            self.pluginRuntimeData = None
