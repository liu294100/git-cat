"""Git hosting providers: detect provider from a remote URL and build web URLs (pure, no network)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

PROVIDERS = ["github", "gitlab", "gitee", "gitea", "bitbucket", "azure", "generic"]
PROVIDER_NAMES = {"github": "GitHub", "gitlab": "GitLab", "gitee": "Gitee", "gitea": "Gitea / Forgejo",
                  "bitbucket": "Bitbucket", "azure": "Azure DevOps", "generic": "Git (other)"}
DEFAULT_HOSTS = {"github": "github.com", "gitlab": "gitlab.com", "gitee": "gitee.com", "gitea": "codeberg.org",
                 "bitbucket": "bitbucket.org", "azure": "dev.azure.com", "generic": ""}
# Where users create personal access tokens (opened from the login dialog).
TOKEN_PAGES = {
    "github": "https://{host}/settings/tokens/new?scopes=repo,workflow,read:user&description=GitCat",
    "gitlab": "https://{host}/-/user_settings/personal_access_tokens?name=GitCat&scopes=api,read_user,write_repository",
    "gitee": "https://{host}/personal_access_tokens/new",
    "gitea": "https://{host}/user/settings/applications",
    "bitbucket": "https://bitbucket.org/account/settings/app-passwords/new",
    "azure": "https://{host}/_usersSettings/tokens",
    "generic": "",
}
SSH_KEY_PAGES = {
    "github": "https://{host}/settings/ssh/new", "gitlab": "https://{host}/-/user_settings/ssh_keys",
    "gitee": "https://{host}/profile/sshkeys", "gitea": "https://{host}/user/settings/keys",
    "bitbucket": "https://bitbucket.org/account/settings/ssh-keys/", "azure": "https://{host}/_usersSettings/keys",
    "generic": "",
}

_SCP = re.compile(r"^(?:(?P<user>[^@/]+)@)?(?P<host>[^:/]+):(?P<path>[^/].*)$")
_URL = re.compile(r"^(?P<scheme>[a-z+]+)://(?:(?P<user>[^@/]+)@)?(?P<host>[^/:]+)(?::(?P<port>\d+))?/(?P<path>.*)$")


@dataclass(frozen=True)
class RemoteInfo:
    provider: str
    host: str
    path: str          # "owner/repo" or "group/sub/repo" (no .git)
    scheme: str = "https"
    user: str = ""

    @property
    def owner(self) -> str:
        return self.path.rsplit("/", 1)[0] if "/" in self.path else ""

    @property
    def repo(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def web(self) -> str:
        if self.provider == "azure":
            # org/project/_git/repo  (ssh form: v3/org/project/repo)
            parts = self.path.split("/")
            if parts and parts[0] == "v3":
                parts = parts[1:]
                if len(parts) == 3:
                    parts = [parts[0], parts[1], "_git", parts[2]]
            return f"https://{self.host.replace('ssh.', '')}/" + "/".join(parts)
        return f"https://{self.host}/{self.path}"

    def commit_url(self, sha: str) -> str:
        sep = {"gitlab": "/-/commit/", "bitbucket": "/commits/", "azure": "/commit/"}.get(self.provider, "/commit/")
        return self.web + sep + sha

    def branch_url(self, branch: str) -> str:
        b = quote(branch, safe="/")
        return {"gitlab": f"{self.web}/-/tree/{b}", "bitbucket": f"{self.web}/branch/{b}",
                "azure": f"{self.web}?version=GB{b}", "gitea": f"{self.web}/src/branch/{b}"}.get(
            self.provider, f"{self.web}/tree/{b}")

    def compare_url(self, base: str, head: str) -> str:
        a, b = quote(base, safe="/"), quote(head, safe="/")
        return {"gitlab": f"{self.web}/-/compare/{a}...{b}",
                "bitbucket": f"{self.web}/branches/compare/{b}%0D{a}",
                "azure": f"{self.web}/branchCompare?baseVersion=GB{a}&targetVersion=GB{b}",
                "gitea": f"{self.web}/compare/{a}...{b}"}.get(self.provider, f"{self.web}/compare/{a}...{b}")

    def new_pr_url(self, branch: str, target: str = "") -> str:
        b = quote(branch, safe="")
        if self.provider == "gitlab":
            url = f"{self.web}/-/merge_requests/new?merge_request[source_branch]={b}"
            return url + (f"&merge_request[target_branch]={quote(target, safe='')}" if target else "")
        if self.provider == "bitbucket":
            return f"{self.web}/pull-requests/new?source={b}" + (f"&dest={quote(target, safe='')}" if target else "")
        if self.provider == "azure":
            return f"{self.web}/pullrequestcreate?sourceRef={b}" + (f"&targetRef={quote(target, safe='')}" if target else "")
        if self.provider == "gitee":
            return f"{self.web}/pulls/new?source={b}" + (f"&target={quote(target, safe='')}" if target else "")
        base = quote(target, safe="/") + "..." if target else ""
        return f"{self.web}/compare/{base}{quote(branch, safe='/')}?expand=1"

    @property
    def ci_url(self) -> str:
        return {"github": f"{self.web}/actions", "gitlab": f"{self.web}/-/pipelines",
                "bitbucket": f"{self.web}/pipelines", "gitea": f"{self.web}/actions",
                "azure": f"{self.web.split('/_git/')[0]}/_build", "gitee": f"{self.web}/gitee_go"}.get(
            self.provider, self.web)


def guess_provider(host: str, known: Optional[dict[str, str]] = None) -> str:
    """known: host -> provider from configured accounts (self-hosted instances)."""
    h = host.lower()
    if known and h in known:
        return known[h]
    if h == "github.com" or h.endswith(".ghe.com") or h.startswith("github."):
        return "github"
    if "gitlab" in h:
        return "gitlab"
    if h in ("gitee.com", "gitee.cn"):
        return "gitee"
    if "bitbucket" in h:
        return "bitbucket"
    if h in ("dev.azure.com", "ssh.dev.azure.com") or h.endswith(".visualstudio.com"):
        return "azure"
    if h in ("codeberg.org", "gitea.com") or "gitea" in h or "forgejo" in h:
        return "gitea"
    return "generic"


def parse_remote(url: str, known: Optional[dict[str, str]] = None) -> Optional[RemoteInfo]:
    u = url.strip()
    m = _URL.match(u)
    if m:
        scheme, user, host, path = m.group("scheme"), m.group("user") or "", m.group("host"), m.group("path")
        if scheme.startswith("ssh"):
            scheme = "ssh"
    else:
        m = _SCP.match(u)
        if not m or "\\" in u or re.match(r"^[A-Za-z]:", u):
            return None  # local path
        scheme, user, host, path = "ssh", m.group("user") or "", m.group("host"), m.group("path")
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if user and ":" in user:
        user = user.split(":", 1)[0]
    if not path or "/" not in path:
        return None
    return RemoteInfo(guess_provider(host, known), host.lower(), path, scheme, user)
