#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import logging
import logging.handlers
import pyftpdlib.servers
import pyftpdlib.handlers
import pyftpdlib.authorizers
import pyftpdlib.filesystems


def loadCfg():
    global cfg

    cfg = json.loads(sys.argv[1])
    if "logFile" not in cfg:
        raise Exception("no \"logFile\" in config file")
    if "logMaxBytes" not in cfg:
        raise Exception("no \"logMaxBytes\" in config file")
    if "logBackupCount" not in cfg:
        raise Exception("no \"logBackupCount\" in config file")
    if "ip" not in cfg:
        raise Exception("no \"ip\" in config file")
    if "port" not in cfg:
        raise Exception("no \"port\" in config file")
    if "dir" not in cfg:
        raise Exception("no \"dir\" in config file")
    if not os.path.isabs(cfg["dir"]) or cfg["dir"].endswith("/"):
        raise Exception("value of \"dir\" is invalid")


def runServer():
    global cfg

    log = logging.getLogger("pyftpdlib")
    log.propagate = False
    log.setLevel(logging.INFO)
    log.addHandler(logging.handlers.RotatingFileHandler(cfg["logFile"], cfg["logMaxBytes"], cfg["logBackupCount"]))

    authorizer = pyftpdlib.authorizers.DummyAuthorizer()
    authorizer.add_anonymous(cfg["dir"], perm="elr")

    handler = pyftpdlib.handlers.FTPHandler
    handler.authorizer = authorizer
    # handler.abstracted_fs = VirtualFS         # FIXME: in future, we need filter function

    server = pyftpdlib.servers.FTPServer((cfg["ip"], cfg["port"]), handler)
    server.serve_forever()


if __name__ == "__main__":
    loadCfg()
    runServer()
