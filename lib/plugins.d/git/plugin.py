#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import hashlib
import pservers.plugin


"""
access-method:
    http-web r
    http-web rw            (user: write)
    git-over-http r
    git-over-http rw       (user: write)

we don't support git-protocol since it does not support one-server-multiple-domain.
"""


def main():
    serverId = pservers.plugin.params["server-id"]
    domainName = pservers.plugin.params["domain-name"]
    dataDir = pservers.plugin.params["data-directory"]
    tmpDir = pservers.plugin.params["temp-directory"]

    # (username, scope, password)
    userInfo = ("write", "klaus", "write")

    # htdigest file
    htdigestFn = os.path.join(tmpDir, "auth-%s.htdigest" % (serverId))
    _Util.generateApacheHtdigestFile(htdigestFn, [userInfo])

    # wsgi script
    wsgiFn = os.path.join(tmpDir, "wsgi-%s.py" % (serverId))
    with open(wsgiFn, "w") as f:
        buf = ''
        buf += '#!/usr/bin/python3\n'
        buf += '# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-\n'
        buf += '\n'
        buf += 'from klaus.contrib.wsgi_autoreloading import make_autoreloading_app\n'
        buf += '\n'
        buf += 'application = make_autoreloading_app("%s", "%s",\n' % (dataDir, serverId)
        buf += '                                     use_smarthttp=True,\n'
        buf += '                                     unauthenticated_push=True,\n'
        buf += '                                     htdigest_file=open("%s"))\n' % (htdigestFn)
        f.write(buf)

    # generate apache config segment
    buf = ''
    buf += '<VirtualHost *>\n'
    buf += '    ServerName %s\n' % (domainName)
    buf += '    WSGIScriptAlias / %s\n' % (wsgiFn)
    buf += '    WSGIChunkedRequest On\n'
    buf += '</VirtualHost>\n'
    buf += '\n'

    # dump result
    json.dump({
        "module-dependencies": {
            "wsgi_module": "mod_wsgi.so",
        },
        "config-segment": buf,
    }, sys.stdout)


class _Util:

    @staticmethod
    def ensureDir(dirname):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    @staticmethod
    def generateApacheHtdigestFile(filename, userInfoList):
        # userInfoList: [(username, realm, password), ...]
        with open(filename, "w") as f:
            for ui in userInfoList:
                f.write(ui[0] + ':' + ui[1] + ':' + hashlib.md5(':'.join(ui).encode("iso8859-1")).hexdigest())
                f.write('\n')


###############################################################################

if __name__ == "__main__":
    main()
