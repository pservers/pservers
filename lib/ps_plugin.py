#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import json
import lxml.etree
from ps_util import PsUtil
from ps_util import DynObject
from ps_param import PsConst


class PsPluginManager:

    def __init__(self, param):
        self.param = param
        self.pluginDict = dict()

    def getPluginNameList(self):
        ret = []
        for pluginName in os.listdir(PsConst.pluginsDir):
            pluginPath = os.path.join(PsConst.pluginsDir, pluginName)
            if not os.path.isdir(pluginPath):
                continue
            ret.append(pluginName)
        return ret

    def getPlugin(self, pluginName):
        if pluginName not in self.pluginDict:
            pluginPath = os.path.join(PsConst.pluginsDir, pluginName)

            # get metadata.xml file
            metadata_file = os.path.join(pluginPath, "metadata.xml")
            if not os.path.exists(metadata_file):
                raise Exception("plugin %s has no metadata.xml" % (pluginName))
            if not os.path.isfile(metadata_file):
                raise Exception("metadata.xml for plugin %s is not a file" % (pluginName))
            if not os.access(metadata_file, os.R_OK):
                raise Exception("metadata.xml for plugin %s is invalid" % (pluginName))

            # check metadata.xml file content
            # FIXME
            rootElem = lxml.etree.parse(metadata_file).getroot()
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

            self.pluginDict[pluginName] = PsPlugin(self.param, pluginName, os.path.join(PsConst.pluginsDir, pluginName), rootElem)

        return self.pluginDict[pluginName]


class PsPlugin:

    def __init__(self, param, pluginName, pluginDir, rootElem):
        # plugin type
        self._pluginType = rootElem.xpath(".//type")[0].text
        if self._pluginType not in ["embedded", "slave-server"]:
            raise Exception("invalid type %s for plugin %s" % (self._pluginType, pluginName))

        # starter
        self._starterExeFile = rootElem.xpath(".//starter")[0].text
        self._starterExeFile = os.path.join(pluginDir, self._starterExeFile)

    @property
    def pluginType(self):
        return self._pluginType

    def start(self, serverId, serverDomainName, serverDataDir):
        tmpDir = os.path.join(PsConst.tmpDir, "serverId")
        PsUtil.ensureDir(tmpDir)

        if self._pluginType == "embedded":
            argument = {
                "server-id": serverId,
                "domain-name": serverDomainName,
                "data-directory": serverDataDir,
                "temp-directory": tmpDir,
            }
            out = PsUtil.cmdCall(self._starterExeFile, json.dumps(argument))
            return (json.loads(out), DynObject())
        elif self._pluginType == "slave-server":
            # FIXME: not implemented
            assert False
        else:
            assert False

    def stop(self, pluginRuntimeData):
        if self._pluginType == "embedded":
            pass
        elif self._pluginType == "slave-server":
            # FIXME: not implemented
            assert False
        else:
            assert False

        tmpDir = os.path.join(PsConst.tmpDir, "serverId")
        PsUtil.forceDelete(tmpDir)
