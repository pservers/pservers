#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import sys
import imp
import time
import dbus
import stat
import prctl
import ctypes
import shutil
import random
import hashlib
import logging
import subprocess
import encodings.idna
from gi.repository import GLib
from OpenSSL import crypto
from dbus.mainloop.glib import DBusGMainLoop


class PsUtil:

    @staticmethod
    def procTerminate(proc, wait=False):
        if proc.poll() is None:
            proc.terminate()
        if wait:
            proc.wait()

    @staticmethod
    def generateApacheHtdigestFile(filename, userInfoList):
        # userInfoList: [(username, realm, password), ...]
        with open(filename, "w") as f:
            for ui in userInfoList:
                f.write(ui[0] + ':' + ui[1] + ':' + hashlib.md5(':'.join(ui).encode("iso8859-1")).hexdigest())
                f.write('\n')

    @staticmethod
    def readFile(filename):
        with open(filename) as f:
            return f.read()

    @staticmethod
    def rreplace(s, sub, dst, count):
        # https://stackoverflow.com/questions/9943504/right-to-left-string-replace-in-python
        return dst.join(s.rsplit(sub, count))

    @staticmethod
    def isPathOverlap(path, pathList):
        for p in pathList:
            if path == p or p.startswith(path + "/") or path.startswith(p + "/"):
                return True
        return False

    @staticmethod
    def cmdCall(cmd, *kargs):
        # call command to execute backstage job
        #
        # scenario 1, process group receives SIGTERM, SIGINT and SIGHUP:
        #   * callee must auto-terminate, and cause no side-effect
        #   * caller must be terminated by signal, not by detecting child-process failure
        # scenario 2, caller receives SIGTERM, SIGINT, SIGHUP:
        #   * caller is terminated by signal, and NOT notify callee
        #   * callee must auto-terminate, and cause no side-effect, after caller is terminated
        # scenario 3, callee receives SIGTERM, SIGINT, SIGHUP:
        #   * caller detects child-process failure and do appopriate treatment

        ret = subprocess.run([cmd] + list(kargs),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
        if ret.returncode > 128:
            # for scenario 1, caller's signal handler has the oppotunity to get executed during sleep
            time.sleep(1.0)
        if ret.returncode != 0:
            print(ret.stdout)
            ret.check_returncode()
        return ret.stdout.rstrip()

    @staticmethod
    def cmdCallWithInput(cmd, inStr, *kargs):
        ret = subprocess.run([cmd] + list(kargs),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             input=inStr, universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)
        if ret.returncode != 0:
            print(ret.stdout)
            ret.check_returncode()
        return ret.stdout.rstrip()

    @staticmethod
    def writePidFile(filename):
        with open(filename, "w") as f:
            f.write(str(os.getpid()))

    @staticmethod
    def preparePersistDir(dirname, uid, gid, mode):
        if not os.path.exists(dirname):
            os.makedirs(dirname, mode)
            if os.getuid() != uid or os.getpid() != gid:
                os.chown(dirname, uid, gid)
        else:
            st = os.stat(dirname)
            if stat.S_IMODE(st.st_mode) != mode:
                os.chmod(dirname, mode)
            if st.st_uid != uid or st.st_gid != gid:
                os.chown(dirname, uid, gid)
                for root, dirs, files in os.walk(dirname):
                    for d in dirs:
                        os.lchown(os.path.join(root, d), uid, gid)
                    for f in files:
                        os.lchown(os.path.join(root, f), uid, gid)

    @staticmethod
    def prepareTransientDir(dirname, uid, gid, mode):
        PsUtil.forceDelete(dirname)
        os.makedirs(dirname, mode)
        if os.getuid() != uid or os.getpid() != gid:
            os.chown(dirname, uid, gid)

    @staticmethod
    def loadObject(filename, classname, *args):
        try:
            f = open(filename)
            m = imp.load_module(filename[:-3], f, filename, ('.py', 'r', imp.PY_SOURCE))
            objClass = getattr(m, classname)
            return objClass(*args)
        except Exception:
            raise Exception("syntax error")

    @staticmethod
    def splitToTuple(s, delimiter):
        return tuple(s.split(delimiter))

    @staticmethod
    def joinLists(lists):
        ret = []
        for tl in lists:
            ret += tl
        return ret

    @staticmethod
    def loadCertAndKey(certFile, keyFile):
        cert = None
        with open(certFile, "rt") as f:
            buf = f.read()
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, buf)

        key = None
        with open(keyFile, "rt") as f:
            buf = f.read()
            key = crypto.load_privatekey(crypto.FILETYPE_PEM, buf)

        return (cert, key)

    @staticmethod
    def genCertAndKey(caCert, caKey, cn, keysize):
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, keysize)

        cert = crypto.X509()
        cert.get_subject().CN = cn
        cert.set_serial_number(random.randint(0, 65535))
        cert.gmtime_adj_notBefore(100 * 365 * 24 * 60 * 60 * -1)
        cert.gmtime_adj_notAfter(100 * 365 * 24 * 60 * 60)
        cert.set_issuer(caCert.get_subject())
        cert.set_pubkey(k)
        cert.sign(caKey, 'sha1')

        return (cert, k)

    @staticmethod
    def dumpCertAndKey(cert, key, certFile, keyFile):
        with open(certFile, "wb") as f:
            buf = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
            f.write(buf)
            os.fchmod(f.fileno(), 0o644)

        with open(keyFile, "wb") as f:
            buf = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
            f.write(buf)
            os.fchmod(f.fileno(), 0o600)

    @staticmethod
    def is_int(s):
        try:
            int(s)
            return True
        except Exception:
            return False

    @staticmethod
    def forceDelete(filename):
        if os.path.islink(filename):
            os.remove(filename)
        elif os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)

    @staticmethod
    def mkDirAndClear(dirname):
        PsUtil.forceDelete(dirname)
        os.mkdir(dirname)

    @staticmethod
    def ensureDir(dirname):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    @staticmethod
    def getFileList(dirName, level, typeList):
        """typeList is a string, value range is "d,f,l,a"
           returns basename"""

        ret = []
        for fbasename in os.listdir(dirName):
            fname = os.path.join(dirName, fbasename)

            if os.path.isdir(fname) and level - 1 > 0:
                for i in PsUtil.getFileList(fname, level - 1, typeList):
                    ret.append(os.path.join(fbasename, i))
                continue

            appended = False
            if not appended and ("a" in typeList or "d" in typeList) and os.path.isdir(fname):        # directory
                ret.append(fbasename)
            if not appended and ("a" in typeList or "f" in typeList) and os.path.isfile(fname):        # file
                ret.append(fbasename)
            if not appended and ("a" in typeList or "l" in typeList) and os.path.islink(fname):        # soft-link
                ret.append(fbasename)

        return ret

    @staticmethod
    def getLineWithoutBlankAndComment(line):
        if line.find("#") >= 0:
            line = line[:line.find("#")]
        line = line.strip()
        return line if line != "" else None

    @staticmethod
    def printInfo(msgStr):
        print(PsUtil.fmt("*", "GOOD") + " " + msgStr)

    @staticmethod
    def printInfoNoNewLine(msgStr):
        print(PsUtil.fmt("*", "GOOD") + " " + msgStr, end="", flush=True)

    @staticmethod
    def fmt(msgStr, fmtStr):
        FMT_GOOD = "\x1B[32;01m"
        FMT_WARN = "\x1B[33;01m"
        FMT_BAD = "\x1B[31;01m"
        FMT_NORMAL = "\x1B[0m"
        FMT_BOLD = "\x1B[0;01m"
        FMT_UNDER = "\x1B[4m"

        for fo in fmtStr.split("+"):
            if fo == "GOOD":
                return FMT_GOOD + msgStr + FMT_NORMAL
            elif fo == "WARN":
                return FMT_WARN + msgStr + FMT_NORMAL
            elif fo == "BAD":
                return FMT_BAD + msgStr + FMT_NORMAL
            elif fo == "BOLD":
                return FMT_BOLD + msgStr + FMT_NORMAL
            elif fo == "UNDER":
                return FMT_UNDER + msgStr + FMT_NORMAL
            else:
                assert False

    @staticmethod
    def waitTcpServiceForProc(ip, port, proc):
        ip = ip.replace(".", "\\.")
        while proc.poll() is None:
            time.sleep(0.1)
            out = PsUtil.cmdCall("/bin/netstat", "-lant")
            m = re.search("tcp +[0-9]+ +[0-9]+ +(%s:%d) +.*" % (ip, port), out)
            if m is not None:
                return
        raise Exception("process terminated")

    @staticmethod
    def touchFile(filename):
        assert not os.path.exists(filename)
        f = open(filename, 'w')
        f.close()

    @staticmethod
    def getSyscallNumber(syscallName):
        # syscallName example: "SYS_prctl"
        out = PsUtil.cmdCallWithInput("/usr/bin/gcc", "#include <sys/syscall.h>\n%s" % (syscallName), "-E", "-")
        syscall_number = out.split("\n")[-1]
        try:
            syscall_number = int(syscall_number)
        except ValueError:
            raise Exception("failed to get syscall number for %s" % (syscallName))
        if not 0 <= syscall_number <= 999:
            raise Exception("failed to get syscall number for %s" % (syscallName))
        return syscall_number


class StdoutRedirector:

    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


class DynObject:
    # an object that can contain abitrary dynamically created properties and methods
    pass


class DropPriviledge:

    def __init__(self, uid, gid, caps=[]):
        assert os.getuid() == 0
        assert os.getgid() == 0

        self._oldInheritable = None
        self._oldAmbient = None
        self._oldKeepCaps = None
        self._oldNoSetuidFixup = None

        if len(caps) > 0:
            assert caps == [prctl.CAP_NET_BIND_SERVICE]                     # FIXME

            # self._oldInheritable =                                        # FIXME
            # self._oldAmbient =                                            # FIXME
            self._oldKeepCaps = prctl.securebits.keep_caps
            self._oldNoSetuidFixup = prctl.securebits.no_setuid_fixup
            prctl.cap_inheritable.net_bind_service = True                   # FIXME, prctl.cap_inheritable.limit() has no effect
            self._capAmbientRaise(caps)                                     # FIXME
            prctl.securebits.keep_caps = True
            prctl.securebits.no_setuid_fixup = True

        os.setresgid(gid, gid, 0)       # must change gid first
        os.setresuid(uid, uid, 0)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        os.setuid(0)
        os.setgid(0)

        if self._oldNoSetuidFixup is not None:
            prctl.securebits.no_setuid_fixup = self._oldNoSetuidFixup
        if self._oldKeepCaps is not None:
            prctl.securebits.keep_caps = self._oldKeepCaps
        if self._oldAmbient is not None:
            assert False            # FIXME
        if self._oldInheritable is not None:
            assert False            # FIXME

    def _capAmbientRaise(self, caps):
        # this function calls SYS_prctl directly, because ambient set is not supported by prctl module yet

        _prctl = ctypes.CDLL(None).syscall
        _prctl.restype = ctypes.c_int
        _prctl.argtypes = ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong

        _PR_CAP_AMBIENT = 47            # from <linux/prctl.h>
        _PR_CAP_AMBIENT_RAISE = 2       # from <linux/prctl.h>

        for cap in caps:
            _prctl(PsUtil.getSyscallNumber("SYS_prctl"), _PR_CAP_AMBIENT, _PR_CAP_AMBIENT_RAISE, cap, 0, 0)


class AvahiDomainNameRegister:

    """
    Exampe:
        obj = AvahiDomainNameRegister()
        obj.add_domain_name(domainName)
        obj.start()
        obj.stop()
    """

    def __init__(self):
        self.retryInterval = 30
        self.interfaceList = []
        self.domainList = []

        self._server = None
        self._retryCreateServerTimer = None
        self._entryGroup = None
        self._retryRegisterTimer = None
        self._ownerChangeHandler = None

    def add_domain_name(self, domain_name):
        assert isinstance(domain_name, str)
        self.domainList.append(domain_name)

    def start(self):
        DBusGMainLoop(set_as_default=True)

        if dbus.SystemBus().name_has_owner("org.freedesktop.Avahi"):
            self._createServer()
        self._ownerChangeHandler = dbus.SystemBus().add_signal_receiver(self.onNameOwnerChanged, "NameOwnerChanged", None, None)

    def stop(self):
        if self._ownerChangeHandler is not None:
            dbus.SystemBus().remove_signal_receiver(self._ownerChangeHandler)
            self._ownerChangeHandler = None
        self._unregister()
        self._releaseServer()

    def onNameOwnerChanged(self, name, old, new):
        if name == "org.freedesktop.Avahi":
            if new != "" and old == "":
                if self._server is None:
                    self._createServer()
                else:
                    # this may happen on some rare case
                    pass
            elif new == "" and old != "":
                self._unregister()
                self._releaseServer()
            else:
                assert False

    def _createServer(self):
        assert self._server is None and self._retryCreateServerTimer is None
        assert self._entryGroup is None
        try:
            self._server = dbus.Interface(dbus.SystemBus().get_object("org.freedesktop.Avahi", "/"), "org.freedesktop.Avahi.Server")
            if self._server.GetState() == 2:    # avahi.SERVER_RUNNING
                self._register()
            self._server.connect_to_signal("StateChanged", self.onSeverStateChanged)
        except Exception:
            logging.error("Avahi create server failed, retry in %d seconds" % (self.retryInterval), exc_info=True)
            self._releaseServer()
            self._retryCreateServer()

    def _releaseServer(self):
        assert self._entryGroup is None
        if self._retryCreateServerTimer is not None:
            GLib.source_remove(self._retryCreateServerTimer)
            self._retryCreateServerTimer = None
        self._server = None

    def onSeverStateChanged(self, state, error):
        if state == 2:      # avahi.SERVER_RUNNING
            self._unregister()
            self._register()
        else:
            self._unregister()

    def _register(self):
        assert self._entryGroup is None and self._retryRegisterTimer is None
        try:
            self._entryGroup = dbus.Interface(dbus.SystemBus().get_object("org.freedesktop.Avahi", self._server.EntryGroupNew()),
                                              "org.freedesktop.Avahi.EntryGroup")
            hostname = self._server.GetHostNameFqdn()
            hostnameRData = self.__encodeRDATA(hostname)
            for domainName in self.domainList:
                self._entryGroup.AddRecord(-1,                                                            # interface = avahi.IF_UNSPEC
                                           0,                                                             # protocol = avahi.PROTO_UNSPEC
                                           dbus.UInt32(0),                                                # flags
                                           self.__encodeCNAME(domainName),                                # name
                                           0x01,                                                          # CLASS_IN
                                           0X05,                                                          # TYPE_CNAME
                                           60,                                                            # TTL
                                           hostnameRData)                                                 # rdata
            self._entryGroup.Commit()
            self._entryGroup.connect_to_signal("StateChanged", self.onEntryGroupStateChanged)
        except Exception:
            logging.error("Avahi register domain name failed, retry in %d seconds" % (self.retryInterval), exc_info=True)
            self._unregister()
            self._retryRegisterService()

    def _unregister(self):
        if self._retryRegisterTimer is not None:
            GLib.source_remove(self._retryRegisterTimer)
            self._retryRegisterTimer = None
        if self._entryGroup is not None:
            try:
                if self._entryGroup.GetState() != 4:        # avahi.ENTRY_GROUP_FAILURE
                    self._entryGroup.Reset()
                    self._entryGroup.Free()
                    # .Free() has mem leaks?
                    self._entryGroup._obj._bus = None
                    self._entryGroup._obj = None
            except dbus.exceptions.DBusException:
                pass
            finally:
                self._entryGroup = None

    def onEntryGroupStateChanged(self, state, error):
        if state in [0, 1, 2]:  # avahi.ENTRY_GROUP_UNCOMMITED, avahi.ENTRY_GROUP_REGISTERING, avahi.ENTRY_GROUP_ESTABLISHED
            pass
        elif state == 3:        # avahi.ENTRY_GROUP_COLLISION
            self._unregister()
            self._retryRegisterService()
        elif state == 4:        # avahi.ENTRY_GROUP_FAILURE
            assert False
        else:
            assert False

    def _retryCreateServer(self):
        assert self._retryCreateServerTimer is None
        self._retryCreateServerTimer = GLib.timeout_add_seconds(self.retryInterval, self.__timeoutCreateServer)

    def __timeoutCreateServer(self):
        self._retryCreateServerTimer = None
        self._createServer()                    # no exception in self._createServer()
        return False

    def _retryRegisterService(self):
        assert self._retryRegisterTimer is None
        self._retryRegisterTimer = GLib.timeout_add_seconds(self.retryInterval, self.__timeoutRegisterService)

    def __timeoutRegisterService(self):
        self._retryRegisterTimer = None
        self._register()                 # no exception in self._register()
        return False

    def __encodeCNAME(self, name):
        return encodings.idna.ToASCII(name)

    def __encodeRDATA(self, name):
        ret = b''
        for part in encodings.idna.ToASCII(name).split(b'.'):
            if part is not None:
                ret += chr(len(part)).encode("iso8859-1")
                ret += part
        ret += b'\0'
        return ret
