"""REST clients for git hosting providers, normalised to one shape (stdlib only).

Normalised records
------------------
user:    {login, name, email, avatar, web}
repo:    {full_name, description, private, https, ssh, updated, web}
run:     {id, name, title, branch, event, status, started, updated, url, sha}
job:     {name, status, started, finished, url, steps: [job-like]}
release: {name, tag, published, assets, kind, url}
status is one of: success failure cancelled skipped running queued manual neutral
"""
from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import quote, urlencode

from ..core.hosting import RemoteInfo

TIMEOUT = 15


class ProviderError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"HTTP {status}: {message}" if status else message)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_STATUS = {
    # GitHub (status/conclusion), GitLab, Bitbucket, Gitea
    "success": "success", "completed": "success", "passed": "success", "successful": "success",
    "failure": "failure", "failed": "failure", "error": "failure", "timed_out": "failure", "startup_failure": "failure",
    "cancelled": "cancelled", "canceled": "cancelled", "stopped": "cancelled",
    "skipped": "skipped", "neutral": "neutral",
    "in_progress": "running", "running": "running",
    "queued": "queued", "pending": "queued", "waiting": "queued", "requested": "queued", "created": "queued",
    "preparing": "queued", "waiting_for_resource": "queued", "scheduled": "queued",
    "manual": "manual", "action_required": "manual",
}


def norm_status(*values: Optional[str]) -> str:
    for v in values:
        if v and v.lower() in _STATUS:
            return _STATUS[v.lower()]
    return "neutral"


class ProviderClient:
    """Base client. Subclasses set FEATURES and implement what they support."""
    FEATURES: frozenset[str] = frozenset()  # user repos ci ci_control dispatch releases

    def __init__(self, host: str, token: str = "", username: str = "", path: str = ""):
        self.host, self.token, self.username, self.path = host, token, username, path

    # ---------------------------------------------------------------- http
    def api_base(self) -> str:
        raise NotImplementedError

    def auth_headers(self) -> dict:
        return {}

    def _req(self, method: str, url: str, body: Optional[dict] = None, params: Optional[dict] = None):
        if not url.startswith("http"):
            url = self.api_base() + url
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json", "User-Agent": "GitCat", **self.auth_headers()}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_context()) as resp:
                raw = resp.read()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read() or b"{}")
                msg = payload.get("message") or payload.get("error") or e.reason
                if isinstance(msg, dict):
                    msg = msg.get("message", str(msg))
            except ValueError:
                msg = str(e.reason)
            raise ProviderError(e.code, str(msg)) from e
        except (OSError, urllib.error.URLError) as e:
            raise ProviderError(0, str(e)) from e

    # ---------------------------------------------------------------- api (defaults)
    def current_user(self) -> dict:
        raise ProviderError(0, "not supported")

    def list_repos(self, limit: int = 100) -> list[dict]:
        return []

    def ci_runs(self, limit: int = 40) -> list[dict]:
        return []

    def ci_jobs(self, run_id) -> list[dict]:
        return []

    def ci_rerun(self, run_id, failed_only: bool = False):
        raise ProviderError(0, "not supported")

    def ci_cancel(self, run_id):
        raise ProviderError(0, "not supported")

    def ci_workflows(self) -> list[dict]:
        return []

    def ci_dispatch(self, workflow_id, ref: str):
        raise ProviderError(0, "not supported")

    def releases(self, limit: int = 30) -> list[dict]:
        return []


# ==================================================================== GitHub / GitHub Enterprise
class GitHubClient(ProviderClient):
    FEATURES = frozenset({"user", "repos", "ci", "ci_control", "dispatch", "releases"})

    def api_base(self) -> str:
        return "https://api.github.com" if self.host == "github.com" else f"https://{self.host}/api/v3"

    def auth_headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def current_user(self) -> dict:
        u = self._req("GET", "/user")
        email = u.get("email") or ""
        if not email:
            try:
                emails = self._req("GET", "/user/emails")
                email = next((e["email"] for e in emails if e.get("primary")), "")
            except ProviderError:
                pass
        return {"login": u.get("login", ""), "name": u.get("name") or u.get("login", ""), "email": email,
                "avatar": u.get("avatar_url", ""), "web": u.get("html_url", "")}

    def list_repos(self, limit: int = 100) -> list[dict]:
        data = self._req("GET", "/user/repos", params={"per_page": min(limit, 100), "sort": "updated",
                                                        "affiliation": "owner,collaborator,organization_member"})
        return [{"full_name": r["full_name"], "description": r.get("description") or "", "private": r.get("private"),
                 "https": r.get("clone_url", ""), "ssh": r.get("ssh_url", ""), "updated": r.get("pushed_at", ""),
                 "web": r.get("html_url", "")} for r in data]

    @property
    def _repo(self) -> str:
        return f"/repos/{self.path}"

    def ci_runs(self, limit: int = 40) -> list[dict]:
        data = self._req("GET", self._repo + "/actions/runs", params={"per_page": limit}).get("workflow_runs", [])
        return [{"id": r["id"], "name": r.get("name", ""), "title": r.get("display_title", ""),
                 "branch": r.get("head_branch", ""), "event": r.get("event", ""),
                 "status": norm_status(r.get("conclusion"), r.get("status")),
                 "started": r.get("run_started_at") or r.get("created_at"), "updated": r.get("updated_at"),
                 "done": r.get("status") == "completed", "url": r.get("html_url", ""), "sha": r.get("head_sha", "")}
                for r in data]

    def ci_jobs(self, run_id) -> list[dict]:
        jobs = self._req("GET", f"{self._repo}/actions/runs/{run_id}/jobs", params={"per_page": 50}).get("jobs", [])
        return [{"name": j.get("name", ""), "status": norm_status(j.get("conclusion"), j.get("status")),
                 "started": j.get("started_at"), "finished": j.get("completed_at"), "url": j.get("html_url", ""),
                 "steps": [{"name": f"{s.get('number', '')}. {s.get('name', '')}",
                            "status": norm_status(s.get("conclusion"), s.get("status")),
                            "started": s.get("started_at"), "finished": s.get("completed_at"),
                            "url": j.get("html_url", ""), "steps": []} for s in j.get("steps", [])]}
                for j in jobs]

    def ci_rerun(self, run_id, failed_only: bool = False):
        return self._req("POST", f"{self._repo}/actions/runs/{run_id}/" +
                         ("rerun-failed-jobs" if failed_only else "rerun"))

    def ci_cancel(self, run_id):
        return self._req("POST", f"{self._repo}/actions/runs/{run_id}/cancel")

    def ci_workflows(self) -> list[dict]:
        wfs = self._req("GET", self._repo + "/actions/workflows", params={"per_page": 100}).get("workflows", [])
        return [{"id": w["id"], "name": f"{w['name']}  ({w['path']})"} for w in wfs if w.get("state") == "active"]

    def ci_dispatch(self, workflow_id, ref: str):
        return self._req("POST", f"{self._repo}/actions/workflows/{workflow_id}/dispatches", {"ref": ref})

    def releases(self, limit: int = 30) -> list[dict]:
        data = self._req("GET", self._repo + "/releases", params={"per_page": limit})
        return [{"name": r.get("name") or r.get("tag_name", ""), "tag": r.get("tag_name", ""),
                 "published": r.get("published_at"), "assets": len(r.get("assets", [])),
                 "kind": "draft" if r.get("draft") else ("prerelease" if r.get("prerelease") else "stable"),
                 "url": r.get("html_url", "")} for r in data]


# ==================================================================== GitLab (gitlab.com + self-managed)
class GitLabClient(ProviderClient):
    FEATURES = frozenset({"user", "repos", "ci", "ci_control", "dispatch", "releases"})

    def api_base(self) -> str:
        return f"https://{self.host}/api/v4"

    def auth_headers(self) -> dict:
        return {"PRIVATE-TOKEN": self.token} if self.token else {}

    def current_user(self) -> dict:
        u = self._req("GET", "/user")
        return {"login": u.get("username", ""), "name": u.get("name", ""),
                "email": u.get("public_email") or u.get("email") or u.get("commit_email") or "",
                "avatar": u.get("avatar_url", ""), "web": u.get("web_url", "")}

    def list_repos(self, limit: int = 100) -> list[dict]:
        data = self._req("GET", "/projects", params={"membership": "true", "per_page": min(limit, 100),
                                                     "order_by": "last_activity_at", "simple": "true"})
        return [{"full_name": p["path_with_namespace"], "description": p.get("description") or "",
                 "private": p.get("visibility") != "public", "https": p.get("http_url_to_repo", ""),
                 "ssh": p.get("ssh_url_to_repo", ""), "updated": p.get("last_activity_at", ""),
                 "web": p.get("web_url", "")} for p in data]

    @property
    def _proj(self) -> str:
        return "/projects/" + quote(self.path, safe="")

    def ci_runs(self, limit: int = 40) -> list[dict]:
        data = self._req("GET", self._proj + "/pipelines", params={"per_page": limit})
        return [{"id": p["id"], "name": f"#{p['id']}", "title": p.get("name") or p.get("ref", ""),
                 "branch": p.get("ref", ""), "event": p.get("source", ""), "status": norm_status(p.get("status")),
                 "started": p.get("created_at"), "updated": p.get("updated_at"),
                 "done": norm_status(p.get("status")) not in ("running", "queued"),
                 "url": p.get("web_url", ""), "sha": p.get("sha", "")} for p in data]

    def ci_jobs(self, run_id) -> list[dict]:
        jobs = self._req("GET", f"{self._proj}/pipelines/{run_id}/jobs", params={"per_page": 100})
        stages: dict[str, dict] = {}
        for j in jobs:
            st = stages.setdefault(j.get("stage", ""), {"name": j.get("stage", ""), "status": "success",
                                                         "started": None, "finished": None, "url": "", "steps": []})
            js = norm_status(j.get("status"))
            st["steps"].append({"name": j.get("name", ""), "status": js, "started": j.get("started_at"),
                                "finished": j.get("finished_at"), "url": j.get("web_url", ""), "steps": []})
            rank = ["failure", "running", "queued", "manual", "cancelled", "success", "skipped", "neutral"]
            if rank.index(js) < rank.index(st["status"]):
                st["status"] = js
            st["url"] = st["url"] or j.get("web_url", "")
        return list(stages.values())

    def ci_rerun(self, run_id, failed_only: bool = False):
        return self._req("POST", f"{self._proj}/pipelines/{run_id}/retry")

    def ci_cancel(self, run_id):
        return self._req("POST", f"{self._proj}/pipelines/{run_id}/cancel")

    def ci_workflows(self) -> list[dict]:
        return [{"id": "pipeline", "name": ".gitlab-ci.yml"}]

    def ci_dispatch(self, workflow_id, ref: str):
        return self._req("POST", self._proj + "/pipeline", {"ref": ref})

    def releases(self, limit: int = 30) -> list[dict]:
        data = self._req("GET", self._proj + "/releases", params={"per_page": limit})
        return [{"name": r.get("name") or r.get("tag_name", ""), "tag": r.get("tag_name", ""),
                 "published": r.get("released_at"), "assets": r.get("assets", {}).get("count", 0),
                 "kind": "prerelease" if r.get("upcoming_release") else "stable",
                 "url": r.get("_links", {}).get("self", "")} for r in data]


# ==================================================================== Gitea / Forgejo / Codeberg
class GiteaClient(ProviderClient):
    FEATURES = frozenset({"user", "repos", "ci", "releases"})

    def api_base(self) -> str:
        return f"https://{self.host}/api/v1"

    def auth_headers(self) -> dict:
        return {"Authorization": f"token {self.token}"} if self.token else {}

    def current_user(self) -> dict:
        u = self._req("GET", "/user")
        return {"login": u.get("login", ""), "name": u.get("full_name") or u.get("login", ""),
                "email": u.get("email", ""), "avatar": u.get("avatar_url", ""),
                "web": f"https://{self.host}/{u.get('login', '')}"}

    def list_repos(self, limit: int = 100) -> list[dict]:
        data = self._req("GET", "/user/repos", params={"limit": min(limit, 50)})
        return [{"full_name": r["full_name"], "description": r.get("description") or "", "private": r.get("private"),
                 "https": r.get("clone_url", ""), "ssh": r.get("ssh_url", ""), "updated": r.get("updated_at", ""),
                 "web": r.get("html_url", "")} for r in data]

    def ci_runs(self, limit: int = 40) -> list[dict]:
        try:
            data = self._req("GET", f"/repos/{self.path}/actions/tasks", params={"limit": limit})
        except ProviderError as e:
            if e.status == 404:
                return []
            raise
        return [{"id": r.get("id"), "name": r.get("name", ""), "title": r.get("display_title", ""),
                 "branch": r.get("head_branch", ""), "event": r.get("event", ""),
                 "status": norm_status(r.get("status")), "started": r.get("run_started_at") or r.get("created_at"),
                 "updated": r.get("updated_at"), "done": norm_status(r.get("status")) not in ("running", "queued"),
                 "url": r.get("url", ""), "sha": r.get("head_sha", "")} for r in data.get("workflow_runs", [])]

    def releases(self, limit: int = 30) -> list[dict]:
        data = self._req("GET", f"/repos/{self.path}/releases", params={"limit": limit})
        return [{"name": r.get("name") or r.get("tag_name", ""), "tag": r.get("tag_name", ""),
                 "published": r.get("published_at"), "assets": len(r.get("assets", [])),
                 "kind": "draft" if r.get("draft") else ("prerelease" if r.get("prerelease") else "stable"),
                 "url": r.get("html_url", "")} for r in data]


# ==================================================================== Gitee
class GiteeClient(ProviderClient):
    FEATURES = frozenset({"user", "repos", "releases"})

    def api_base(self) -> str:
        return "https://gitee.com/api/v5"

    def _req(self, method, url, body=None, params=None):
        params = dict(params or {})
        if self.token:
            params["access_token"] = self.token
        return super()._req(method, url, body, params)

    def current_user(self) -> dict:
        u = self._req("GET", "/user")
        return {"login": u.get("login", ""), "name": u.get("name") or u.get("login", ""),
                "email": u.get("email") or "", "avatar": u.get("avatar_url", ""), "web": u.get("html_url", "")}

    def list_repos(self, limit: int = 100) -> list[dict]:
        data = self._req("GET", "/user/repos", params={"per_page": min(limit, 100), "sort": "pushed"})
        return [{"full_name": r["full_name"], "description": r.get("description") or "", "private": r.get("private"),
                 "https": r.get("html_url", "") + ".git", "ssh": r.get("ssh_url", ""), "updated": r.get("pushed_at", ""),
                 "web": r.get("html_url", "")} for r in data]

    def releases(self, limit: int = 30) -> list[dict]:
        data = self._req("GET", f"/repos/{self.path}/releases", params={"per_page": limit, "direction": "desc"})
        return [{"name": r.get("name") or r.get("tag_name", ""), "tag": r.get("tag_name", ""),
                 "published": r.get("created_at"), "assets": len(r.get("assets", [])),
                 "kind": "prerelease" if r.get("prerelease") else "stable",
                 "url": f"https://gitee.com/{self.path}/releases/tag/{r.get('tag_name', '')}"} for r in data]


# ==================================================================== Bitbucket Cloud
class BitbucketClient(ProviderClient):
    FEATURES = frozenset({"user", "repos", "ci"})

    def api_base(self) -> str:
        return "https://api.bitbucket.org/2.0"

    def auth_headers(self) -> dict:
        if not self.token:
            return {}
        if self.username:  # app password
            raw = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()
            return {"Authorization": f"Basic {raw}"}
        return {"Authorization": f"Bearer {self.token}"}  # access token

    def current_user(self) -> dict:
        u = self._req("GET", "/user")
        return {"login": u.get("username") or u.get("nickname", ""), "name": u.get("display_name", ""),
                "email": "", "avatar": u.get("links", {}).get("avatar", {}).get("href", ""),
                "web": u.get("links", {}).get("html", {}).get("href", "")}

    def list_repos(self, limit: int = 100) -> list[dict]:
        data = self._req("GET", "/repositories", params={"role": "member", "pagelen": min(limit, 100),
                                                         "sort": "-updated_on"}).get("values", [])
        res = []
        for r in data:
            clones = {c["name"]: c["href"] for c in r.get("links", {}).get("clone", [])}
            res.append({"full_name": r.get("full_name", ""), "description": r.get("description") or "",
                        "private": r.get("is_private"), "https": clones.get("https", ""), "ssh": clones.get("ssh", ""),
                        "updated": r.get("updated_on", ""), "web": r.get("links", {}).get("html", {}).get("href", "")})
        return res

    def ci_runs(self, limit: int = 40) -> list[dict]:
        data = self._req("GET", f"/repositories/{self.path}/pipelines/",
                         params={"sort": "-created_on", "pagelen": min(limit, 100)}).get("values", [])
        res = []
        for p in data:
            st = p.get("state", {})
            target = p.get("target", {})
            res.append({"id": p.get("uuid"), "name": f"#{p.get('build_number', '')}",
                        "title": target.get("commit", {}).get("message", "").split("\n")[0] if target.get("commit") else "",
                        "branch": target.get("ref_name", ""), "event": p.get("trigger", {}).get("name", ""),
                        "status": norm_status(st.get("result", {}).get("name"), st.get("stage", {}).get("name"),
                                              st.get("name")),
                        "started": p.get("created_on"), "updated": p.get("completed_on"),
                        "done": st.get("name") == "COMPLETED",
                        "url": f"https://bitbucket.org/{self.path}/pipelines/results/{p.get('build_number', '')}",
                        "sha": target.get("commit", {}).get("hash", "")})
        return res


# ==================================================================== Azure DevOps
class AzureClient(ProviderClient):
    FEATURES = frozenset({"user"})

    def api_base(self) -> str:
        return "https://app.vssps.visualstudio.com/_apis"

    def auth_headers(self) -> dict:
        if not self.token:
            return {}
        return {"Authorization": "Basic " + base64.b64encode(f":{self.token}".encode()).decode()}

    def current_user(self) -> dict:
        u = self._req("GET", "/profile/profiles/me", params={"api-version": "7.1"})
        return {"login": u.get("emailAddress") or u.get("publicAlias", ""), "name": u.get("displayName", ""),
                "email": u.get("emailAddress", ""), "avatar": "", "web": ""}


CLIENTS: dict[str, type[ProviderClient]] = {
    "github": GitHubClient, "gitlab": GitLabClient, "gitea": GiteaClient, "gitee": GiteeClient,
    "bitbucket": BitbucketClient, "azure": AzureClient,
}


def client_for(provider: str, host: str, token: str = "", username: str = "", path: str = "") -> ProviderClient:
    cls = CLIENTS.get(provider, ProviderClient)
    return cls(host, token, username, path)


def client_for_remote(info: RemoteInfo, token: str = "", username: str = "") -> ProviderClient:
    return client_for(info.provider, info.host, token, username, info.path)
