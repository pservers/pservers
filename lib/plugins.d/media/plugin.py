#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import sys
import json
import pservers.plugin


"""
access-method:
    http-web r
    http-web rw             (user: write)
    httpdir r               (url-postfix: /pub)
    rstp-over-http r        (url-postfix: /stream)

we don't support ftp-protocol because very few server/client supports one-server-multiple-domain.
we don't support rstp-protocol because it does not support one-server-multiple-domain.
"""


def main():
    serverId = pservers.plugin.params["server-id"]
    dataDir = pservers.plugin.params["data-directory"]

    buf = ''
    buf += '<VirtualHost *>\n'
    buf += '    ServerName %s\n' % (serverId)
    buf += '    DocumentRoot "%s"\n' % (dataDir)
    buf += '    <Directory "%s">\n' % (dataDir)
    buf += '        Options Indexes\n'
    buf += '        Require all granted\n'
    buf += '    </Directory>\n'
    buf += '</VirtualHost>\n'

    # dump result
    json.dump({
        "module-dependencies": [],
        "config-segment": buf,
    }, sys.stdout)


###############################################################################

if __name__ == "__main__":
    main()
