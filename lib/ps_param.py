#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import pwd
import grp


class PsConst:

    etcDir = "/etc/pservers"
    libDir = "/usr/lib/pservers"
    pluginsDir = os.path.join(libDir, "plugins")
    serversDir = os.path.join(libDir, "servers")

    varDir = "/var/lib/pservers"
    logDir = "/var/log/pservers"
    runDir = "/run/pservers"
    tmpDir = "/tmp/pservers"                            # FIXME
    tmpWebRootDir = os.path.join(tmpDir, "web-root")

    user = "pservers"
    group = "pservers"
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid

    updaterLogFileSize = 10 * 1024 * 1024
    updaterLogFileCount = 2

    httpPort = 80
    httpsPort = 443                     # FIXME

    mainCfgFile = os.path.join(etcDir, "main.conf")
    pidFile = os.path.join(runDir, "pservers.pid")
    apiServerFile = os.path.join(runDir, "api.socket")


class PsParam:

    def __init__(self):
        self.serverDict = dict()

        self.listenIp = "0.0.0.0"

        # objects
        self.mainloop = None
        self.pluginManager = None
        self.mainServer = None
        self.avahiObj = None
        self.apiServer = None
