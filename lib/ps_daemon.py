#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import prctl
import signal
import shutil
import logging
import asyncio
import asyncio_glib
from ps_util import PsUtil
from ps_util import DropPriviledge
from ps_util import StdoutRedirector
from ps_util import AvahiDomainNameRegister
from ps_param import PsConst
from ps_plugin import PsPluginManager
from ps_server import PsServerManager
from ps_main_httpd import PsMainHttpServer


class PsDaemon:

    def __init__(self, param):
        self.param = param

    def run(self):
        self._loadMainCfg()
        try:
            # create directories
            PsUtil.preparePersistDir(PsConst.varDir, PsConst.uid, PsConst.gid, 0o755)
            PsUtil.preparePersistDir(PsConst.logDir, PsConst.uid, PsConst.gid, 0o755)
            PsUtil.prepareTransientDir(PsConst.runDir, PsConst.uid, PsConst.gid, 0o755)
            PsUtil.prepareTransientDir(PsConst.tmpDir, PsConst.uid, PsConst.gid, 0o755)

            with DropPriviledge(PsConst.uid, PsConst.gid, caps=[prctl.CAP_NET_BIND_SERVICE]):
                try:
                    # initialize logging
                    sys.stdout = StdoutRedirector(os.path.join(PsConst.logDir, "pservers.out"))
                    sys.stderr = sys.stdout

                    logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
                    logging.getLogger().setLevel(logging.INFO)
                    logging.info("Program begins.")

                    # create mainloop
                    asyncio.set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())
                    self.param.mainloop = asyncio.get_event_loop()

                    # write pid file
                    PsUtil.writePidFile(PsConst.pidFile)

                    # plugin manager
                    self.pluginManager = PsPluginManager(self.param)

                    # load servers
                    self.serverManager = PsServerManager(self.param)
                    self.serverManager.loadServers()
                    if len(self.param.serverDict) == 0:
                        raise Exception("no server loaded")
                    logging.info("Servers loaded: %s" % (",".join(sorted(self.param.serverDict.keys()))))

                    # register domain names
                    self.param.avahiObj = AvahiDomainNameRegister()
                    for serverObj in self.param.serverDict.values():
                        self.param.avahiObj.add_domain_name(serverObj.domainName)
                    self.param.avahiObj.start()

                    # main server
                    self.param.mainServer = PsMainHttpServer(self.param)
                    for serverObj in self.param.serverDict.values():
                        cfgSeg = serverObj.startAndGetMainHttpServerCfgSegment()
                        self.param.mainServer.addCfgSeg(cfgSeg)
                    self.param.mainServer.start()
                    logging.info("Main server started, listening on port %d." % (PsConst.httpPort))

                    # start main loop
                    logging.info("Mainloop begins.")
                    self.param.mainloop.add_signal_handler(signal.SIGINT, self._sigHandlerINT)
                    self.param.mainloop.add_signal_handler(signal.SIGTERM, self._sigHandlerTERM)
                    self.param.mainloop.run_forever()
                    logging.info("Mainloop exits.")
                finally:
                    if self.param.avahiObj is not None:
                        self.param.avahiObj.stop()
                    if self.param.mainServer is not None:
                        self.param.mainServer.dispose()
                    logging.shutdown()
        finally:
            shutil.rmtree(PsConst.tmpDir)
            shutil.rmtree(PsConst.runDir)

    def _loadMainCfg(self):
        if not os.path.exists(PsConst.mainCfgFile):
            return

        buf = PsUtil.readFile(PsConst.mainCfgFile)
        if buf == "":
            return

        dataObj = json.loads(buf)
        if "listenIp" in dataObj:
            self.param.listenIp = dataObj["listenIp"]

    def _sigHandlerINT(self):
        logging.info("SIGINT received.")
        self.param.mainloop.stop()
        return True

    def _sigHandlerTERM(self):
        logging.info("SIGTERM received.")
        self.param.mainloop.stop()
        return True
