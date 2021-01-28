#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import pservers.plugin


"""
access method:
    http-ui r
    http-ui rw       (user: rw)
    http-webdav r    (url-postfix: /webdav)
    http-webdav rw   (url-postfix: /webdav) (user: rw)
    httpdir r        (url-postfix: /pub)

we don't support ftp-protocol because very few server/client supports one-server-multiple-domain.
"""


def main():
    domainName = pservers.plugin.params["domain-name"]
    dataDir = pservers.plugin.params["data-directory"]
    tmpDir = pservers.plugin.params["temp-directory"]
    webRootDir = pservers.plugin.params["webroot-directory"]

    webdavDir = os.path.join(webRootDir, "webdav")
    os.symlink(dataDir, webdavDir)

    pubDir = os.path.join(webRootDir, "pub")
    os.symlink(dataDir, pubDir)

    buf = ''
    buf += 'ServerName %s\n' % (domainName)
    buf += 'DocumentRoot "%s"\n' % (webRootDir)
    buf += 'DavLockDB "%s"\n' % (os.path.join(tmpDir, "DavLock"))
    buf += '<Directory "%s">\n' % (webRootDir)
    buf += '    Require all granted\n'
    buf += '</Directory>\n'
    buf += '<Directory "%s">\n' % (webdavDir)
    buf += '    Dav filesystem\n'
    buf += '    Require all granted\n'
    buf += '</Directory>\n'
    buf += '<Directory "%s">\n' % (pubDir)
    buf += '    Options Indexes\n'
    buf += '    Require all granted\n'
    buf += '</Directory>\n'

    # dump result
    json.dump({
        "module-dependencies": {},
        "config-segment": buf,
    }, sys.stdout)


###############################################################################

if __name__ == "__main__":
    main()
