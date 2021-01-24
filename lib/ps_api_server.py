#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import logging
from ps_util import UnixDomainSocketApiServer
from ps_param import PsConst


# FIXME
# 1. no error report to client
# 2. perhaps should use json-rpc
# 3. low-priority, client should use client library
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
            logging.info("%s disappeared." % (self._toDebugStr(self._clientDict[sock])))
        del self._clientDict[sock]

    def _clientNotifyFunc(self, sock, data):
        # check
        if "domain-name" not in data:
            raise Exception("\"domain-name\" field does not exist in notification")
        if "http-port" not in data and "https-port" not in data:
            raise Exception("\"http-port\" or \"https-port\" must exist in notification")

        # do work and save log
        cfgId = "proxy-%d" % (sock.fileno())
        if self._clientDict[sock] is None:
            self.param.mainServer.addConfig(cfgId, self._toApacheConfig(data))
        else:
            self.param.mainServer.updateConfig(cfgId, self._toApacheConfig(data))
            if data["domain-name"] != self._clientDict[sock]["domain-name"]:
                self.param.avahiObj.remove_domain_name(self._clientDict[sock]["domain-name"])
                self.param.avahiObj.add_domain_name(data["domain-name"])
        logging.info("%s registered." % (self._toDebugStr(data)))

        # record data
        self._clientDict[sock] = data
        logging.info("URL \"http://%s\" is available for access." % (self._clientDict[sock]["domain-name"]))

    def _toDebugStr(self, data):
        tlist = []
        if "http-port" in data:
            tlist.append("http:%d" % (data["http-port"]))
        if "https-port" in data:
            tlist.append("https:%d" % (data["http-port"]))
        return "pserver \"%s,%s\"" % (data["domain-name"], ",".join(tlist))

    def _toApacheConfig(self, data):
        # FIXME: not implemented: https, http2, websocket, multiple-proxypass-directive ordering
        assert "http-port" in data and "https-port" not in data

        buf = ''
        buf += '<VirtualHost *>\n'
        buf += '    ServerName %s\n' % (data["domain-name"])
        buf += '    ProxyPass / "http://127.0.0.1:%d"\n' % (data["http-port"])
        buf += '    ProxyPassReverse / "http://127.0.0.1:%d"\n' % (data["http-port"])
        buf += '</VirtualHost>\n'
        buf += '\n'

        return {
            "module-dependencies": {
                "proxy_module": "mod_proxy.so",
                "proxy_http_module": "mod_proxy_http.so",
            },
            "config-segment": buf,
        }
