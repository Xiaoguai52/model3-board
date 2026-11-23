#!/usr/bin/env python3
"""Server patch: make cmd_server.refresh_token() persist the rotated
refresh token. Tesla issues a NEW refresh_token on every refresh;
the old code saved only the access_token and threw the new refresh
token away, so the stored one aged out and died on 2026-11-24
(login_required / "The refresh_token is expired").
Anchor-based; backs up first; restores on compile failure.
"""
import py_compile
import shutil
import sys

PATH = "/home/ubuntu/tesla-fleet/cmd_server.py"
src = open(PATH, encoding="utf-8").read()

if "new_refresh" in src:
    print("refresh patch already present, nothing to do")
    sys.exit(0)

OLD = """    new_token = data.get("access_token")
    if not new_token:
        return None
    with open(ACCESS_FILE, "w") as f:
        f.write(new_token)
    os.chmod(ACCESS_FILE, 0o600)
    return new_token"""

NEW = """    new_token = data.get("access_token")
    if not new_token:
        return None
    with open(ACCESS_FILE, "w") as f:
        f.write(new_token)
    os.chmod(ACCESS_FILE, 0o600)
    new_refresh = data.get("refresh_token")
    if new_refresh:
        with open(REFRESH_FILE, "w") as f:
            f.write(new_refresh)
        os.chmod(REFRESH_FILE, 0o600)
    return new_token"""

assert src.count(OLD) == 1, "refresh_token anchor not found exactly once"
src = src.replace(OLD, NEW)
shutil.copy2(PATH, PATH + ".bak-refresh")
open(PATH, "w", encoding="utf-8").write(src)
try:
    py_compile.compile(PATH, doraise=True)
except Exception as exc:
    shutil.copy2(PATH + ".bak-refresh", PATH)
    print("compile failed, backup restored:", exc)
    sys.exit(1)
print("refresh patch applied and compiles")
