#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import glob
import json
import libxml2
from ps_util import PsUtil
from ps_param import PsConst


class PsServerManager:

    def __init__(self, param):
        self.param = param

    def loadPlugins(self):
        for fn in glob.glob(PsConst.pluginCfgFileGlobPattern):
            pluginName = PsUtil.rreplace(os.path.basename(fn).replace("plugin-", "", 1), ".conf", "", 1)
            pluginPath = os.path.join(PsConst.serversDir, pluginName)
            if not os.path.isdir(pluginPath):
                continue
            pluginCfg = dict()
            with open(os.path.join(PsConst.etcDir, fn), "r") as f:
                buf = f.read()
                if buf != "":
                    pluginCfg = json.loads(buf)
            self._load(pluginName, pluginPath, pluginCfg)

    def _load(self, name, path, cfgDict):
        # get metadata.xml file
        metadata_file = os.path.join(path, "metadata.xml")
        if not os.path.exists(metadata_file):
            raise Exception("plugin %s has no metadata.xml" % (name))
        if not os.path.isfile(metadata_file):
            raise Exception("metadata.xml for plugin %s is not a file" % (name))
        if not os.access(metadata_file, os.R_OK):
            raise Exception("metadata.xml for plugin %s is invalid" % (name))

        # check metadata.xml file content
        # FIXME
        tree = libxml2.parseFile(metadata_file)
        # if True:
        #     dtd = libxml2.parseDTD(None, constants.PATH_PLUGIN_DTD_FILE)
        #     ctxt = libxml2.newValidCtxt()
        #     messages = []
        #     ctxt.setValidityErrorHandler(lambda item, msgs: msgs.append(item), None, messages)
        #     if tree.validateDtd(ctxt, dtd) != 1:
        #         msg = ""
        #         for i in messages:
        #             msg += i
        #         raise exceptions.IncorrectPluginMetaFile(metadata_file, msg)

        # get data from metadata.xml file
        root = tree.getRootElement()

        # create PsServer objects
        obj = PsServer(self.param, path, root.xpathEval(".//server")[0], cfgDict)
        assert obj.id not in self.param.serverDict
        self.param.serverDict[obj.id] = obj


class PsServer:

    def __init__(self, param, pluginDir, rootElem, cfgDict):
        self.id = rootElem.prop("id")
        self.cfgDict = cfgDict

        # data directory
        self.dataDir = os.path.join(PsConst.varDir, self.id)
        PsUtil.ensureDir(self.dataDir)

        # domain name
        self.domainName = rootElem.xpathEval(".//domain-name")[0].getContent()
        if not self.domainName.endswith(".private"):
            raise Exception("server %s: invalid domain-name %s" % (self.id, self.domainName))
        # FIXME
        self.domainName = self.domainName.replace(".private", ".local")

        # server type
        self.serverType = rootElem.xpathEval(".//server-type")[0].getContent()
        if self.serverType not in ["file", "git"]:
            raise Exception("server %s: invalid server type %s" % (self.id, self.serverType))
