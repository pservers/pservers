#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import pservers.plugin


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
    print(buf)


###############################################################################

if __name__ == "__main__":
    main()
