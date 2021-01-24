#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

# client.py - pserver client library
#
# Copyright (c) 2005-2020 Fpemud <fpemud@sina.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
mirrors.pservers

@author: Fpemud
@license: GPLv3 License
@contact: fpemud@sina.com
"""

import os
import socket
import logging
from gi.repository import GLib

__author__ = "fpemud@sina.com (Fpemud)"
__version__ = "0.0.1"


class SimpleClient:

    def __init__(self):
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(_socketFile)

    def close(self):
        self._sock.close()
        del self._sock

    def register(self, domain_name, http_port=None, https_port=None):
        data = _registerParamToData(domain_name, http_port, https_port)
        self._sock.send(data.encode("utf-8"))
        self._sock.send(b'\n')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class PersistClientGLib:

    """
    Exampe:
        obj = PersistClientGLib()
        obj.register(domainName, urlMap)
        obj.start()
        obj.register(domainName, urlMap)
        obj.stop()
    """

    def __init__(self):
        self.retryInterval = 30

        self._sock = None
        self._sockWatch = None
        self._retryCreateSocketTimer = None

        self._data = None

    def start(self):
        self._createSocket()
        if self._sock is not None:
            self._register()

    def stop(self):
        self._data = None
        if self._retryCreateSocketTimer is not None:
            GLib.source_remove(self._retryCreateSocketTimer)
            self._retryCreateSocketTimer = None
        if self._sock is not None:
            self._closeSocket()

    def register(self, domain_name, http_port=None, https_port=None):
        self._data = _registerParamToData(domain_name, http_port, https_port)
        if self._sock is not None:
            self._register()

    def onRecv(self, source, cb_condition):
        logging.error("pserver connection aborted, retry in %d seconds" % (self.retryInterval), exc_info=True)
        self._closeSocket()
        self._retryCreateSocket()
        return False

    def _createSocket(self):
        assert self._sock is None
        assert self._sockWatch is None
        assert self._retryCreateSocketTimer is None

        if not os.path.exists(_socketFile):
            self._retryCreateSocket()
            return

        try:
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._sock.connect(_socketFile)
            self._sockWatch = GLib.io_add_watch(self._sock, GLib.IO_IN | GLib.IO_PRI | GLib.IO_ERR | GLib.IO_HUP | GLib.IO_NVAL, self.onRecv)
        except Exception:
            logging.error("connect to pserver failed, retry in %d seconds" % (self.retryInterval), exc_info=True)
            self._closeSocket()
            self._retryCreateSocket()

    def _closeSocket(self):
        if self._sockWatch is not None:
            GLib.source_remove(self._sockWatch)
            self._sockWatch = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def _register(self):
        assert self._sock is not None

        if self._data is None:
            return

        try:
            self._sock.send(self._data.encode("utf-8"))
            self._sock.send(b'\n')
        except Exception:
            logging.error("register to pserver failed, retry in %d seconds" % (self.retryInterval), exc_info=True)
            self._closeSocket()
            self._retryCreateSocket()

    def _retryCreateSocket(self):
        assert self._retryCreateSocketTimer is None
        self._retryCreateSocketTimer = GLib.timeout_add_seconds(self.retryInterval, self.__timeoutCreateSocket)

    def __timeoutCreateSocket(self):
        self._retryCreateSocketTimer = None
        self._createSocket()                    # no exception in self._createSocket()
        self._register()                        # no exception in self._register()
        return False


_socketFile = "/run/pservers/api.socket"


def _registerParamToData(domain_name, http_port=None, https_port=None):
    assert isinstance(domain_name, str)
    assert http_port is not None or https_port is not None
    if http_port is not None:
        assert isinstance(domain_name, int) and 0 < http_port < 65536
    if https_port is not None:
        assert isinstance(domain_name, int) and 0 < https_port < 65536

    data = {
        "domain-name": domain_name,
    }
    if http_port is not None:
        data["http-port"] = http_port
    if https_port is not None:
        data["https-port"] = https_port

    return data
