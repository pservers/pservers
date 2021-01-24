#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

from ps_util import UnixDomainSocketApiServer
from ps_param import PsConst


class PsApiServer(UnixDomainSocketApiServer):

    def __init__(self, param):
        self.param = param
        self._clientDict = dict()
        super().__init__(PsConst.apiServerFile, self._clientAppearFunc, self._clientDisappearFunc, self._clientNotifyFunc)

    def dispose(self):
        self.param.mainServer.batchRemoveConfig(self._clientDict.keys())
        super().dispose()

    def _clientAppearFunc(self, sock):
        assert sock not in self._clientDict
        self._clientDict[sock] = None
        return sock

    def _clientDisappearFunc(self, sock):
        assert sock in self._clientDict
        if self._clientDict[sock] is not None:
            self.param.mainServer.removeConfig(sock.fileno())
        del self._clientDict[sock]

    def _clientNotifyFunc(self, sock, data):
        cfgId = "proxy-%d" % (sock.fileno())
        if self._clientDict[sock] is None:
            self.param.mainServer.addConfig(cfgId, self._toApacheConfig(data))
        else:
            self.param.mainServer.updateConfig(cfgId, self._toApacheConfig(data))
        self._clientDict[sock] = data

    def _toApacheConfig(data):
        # FIXME: not implemented: http2, websocket, multiple-proxypass-directive ordering

        if "domain-name" not in data:
            raise Exception("\"domain-name\" field does not exist in notification")
        if "url-map" not in data:
            raise Exception("\"url-map\" field does not exist in notification")

        buf = ''
        buf += '<VirtualHost *>\n'
        buf += '    ServerName %s\n' % (data["domain-name"])
        for src, dst in data["url-map"].items():
            buf += '    ProxyPass "%s" "%s"\n' % (src, dst)
            buf += '    ProxyPassReverse "%s" "%s"\n' % (src, dst)
        buf += '</VirtualHost>\n'
        buf += '\n'

        return {
            "module-dependencies": {
                "proxy_module": "mod_proxy.so",
                "proxy_http_module": "mod_proxy_http.so",
            },
            "config-segment": buf,
        }
