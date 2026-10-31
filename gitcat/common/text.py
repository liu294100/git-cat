"""Pure text helpers: remote URL to web URL, relative time, initials, fuzzy matching."""
from __future__ import annotations

import time

from .i18n import t


def remote_web_url(url: str) -> str:
    u = url.strip()
    if u.startswith("git@"):
        host, _, path = u[4:].partition(":")
        u = f"https://{host}/{path}"
    elif u.startswith("ssh://"):
        rest = u[6:].split("@", 1)[-1]
        host, _, path = rest.partition("/")
        u = f"https://{host.split(':')[0]}/{path}"
    elif "@" in u.split("//", 1)[-1].split("/", 1)[0]:
        scheme, rest = u.split("//", 1)
        u = scheme + "//" + rest.split("@", 1)[1]
    if u.endswith(".git"):
        u = u[:-4]
    return u.rstrip("/")


def initials(name: str) -> str:
    parts = [p for p in name.replace(".", " ").replace("_", " ").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper() if parts[0].isascii() else parts[0][:1]
    return (parts[0][:1] + parts[1][:1]).upper()


def relative_time(ts: int) -> str:
    d = int(time.time()) - ts
    if d < 60:
        return t("time.now")
    for limit, div, key in ((3600, 60, "time.minutes"), (86400, 3600, "time.hours"), (86400 * 30, 86400, "time.days"),
                            (86400 * 365, 86400 * 30, "time.months")):
        if d < limit:
            return t(key, n=d // div)
    return t("time.years", n=d // (86400 * 365))
