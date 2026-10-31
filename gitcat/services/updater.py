"""Self-update from GitHub Releases (same scheme as kiro-ip-guard: SHA256SUMS + onefile zip)."""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote, unquote, urlparse

from .. import APP_NAME, GITHUB_REPOSITORY

GITHUB_LATEST_RELEASE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
GITHUB_DOWNLOAD_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/download"
CHECKSUM_ASSET = "SHA256SUMS"
MAX_DOWNLOAD_BYTES = 400 * 1024 * 1024
EXE_NAME = "GitCat.exe"
_VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+)*)$")
_OLD_SUFFIX = ".old"
_NEW_SUFFIX = ".new"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    html_url: str
    tag: str = ""


def _version_parts(value: str) -> tuple[int, ...]:
    match = _VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Unsupported release version: {value}")
    parts = tuple(int(part) for part in match.group(1).split("."))
    while len(parts) > 1 and parts[-1] == 0:
        parts = parts[:-1]
    return parts


def is_newer_version(candidate: str, current: str) -> bool:
    a, b = _version_parts(candidate), _version_parts(current)
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def check_latest_release(current_version: str, timeout: int = 8) -> Optional[ReleaseInfo]:
    """Resolve GitHub's /releases/latest redirect (no API rate limit)."""
    request = urllib.request.Request(GITHUB_LATEST_RELEASE_URL,
                                     headers={"User-Agent": f"{APP_NAME}/{current_version}"}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            html_url = response.geturl()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(str(exc)) from exc
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(str(exc)) from exc
    parsed = urlparse(html_url)
    releases_path = f"/{GITHUB_REPOSITORY}/releases"
    tag_prefix = releases_path + "/tag/"
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise RuntimeError("GitHub returned an unexpected release URL")
    if parsed.path.rstrip("/") == releases_path:
        return None
    if not parsed.path.startswith(tag_prefix):
        raise RuntimeError("GitHub returned an unexpected release URL")
    tag = unquote(parsed.path[len(tag_prefix):]).strip("/")
    try:
        if not is_newer_version(tag, current_version):
            return None
    except ValueError:
        return None
    return ReleaseInfo(tag.removeprefix("v"), html_url, tag)


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _current_target() -> Optional[Path]:
    if not _is_frozen():
        return None
    executable = Path(sys.executable).resolve()
    system = platform.system()
    if system == "Windows":
        return executable
    if system == "Darwin":
        bundle = executable.parents[2] if len(executable.parents) >= 3 else None
        if bundle is not None and bundle.suffix == ".app":
            return bundle
    return None


def release_asset_name(version: str, system: Optional[str] = None, machine: Optional[str] = None) -> Optional[str]:
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if machine in {"amd64", "x86_64", "x64"}:
        arch = "x64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        return None
    if system == "Windows":
        return f"GitCat-Windows-{arch}-onefile-v{version}.zip"
    if system == "Darwin":
        return f"GitCat-macOS-{arch}-onefile-v{version}.zip"
    return None


def can_self_update() -> bool:
    target = _current_target()
    if target is None or "AppTranslocation" in str(target):
        return False
    return os.access(target.parent, os.W_OK)


def _download(url: str, destination: Path, user_agent: str, timeout: int,
              progress: Optional[Callable[[str, int], None]] = None) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            if urlparse(response.geturl()).scheme != "https":
                raise RuntimeError("Download was redirected to a non-HTTPS URL")
            declared = int(response.headers.get("Content-Length") or 0)
            if declared > MAX_DOWNLOAD_BYTES:
                raise RuntimeError("Release asset is too large")
            received = 0
            with destination.open("wb") as stream:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_DOWNLOAD_BYTES:
                        raise RuntimeError("Release asset is too large")
                    stream.write(chunk)
                    if progress and declared:
                        progress("download", min(100, received * 100 // declared))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{url}: HTTP {exc.code}") from exc
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"{url}: {exc}") from exc


def _expected_sha256(checksums: str, asset: str) -> str:
    for line in checksums.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset:
            digest = parts[0].lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                return digest
    raise RuntimeError(f"{CHECKSUM_ASSET} has no entry for {asset}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _swap_into_place(target: Path, staged: Path) -> None:
    """A running executable can be renamed but not overwritten."""
    backup = target.with_name(target.name + _OLD_SUFFIX)
    if backup.exists():
        _remove_path(backup)
    os.replace(target, backup)
    try:
        os.replace(staged, target)
    except OSError:
        os.replace(backup, target)
        raise


def _extract_windows(archive: Path, target: Path) -> Path:
    staged = target.with_name(target.name + _NEW_SUFFIX)
    with zipfile.ZipFile(archive) as bundle:
        members = [i for i in bundle.infolist()
                   if not i.is_dir() and Path(i.filename.replace("\\", "/")).name.lower() == EXE_NAME.lower()]
        if not members:
            raise RuntimeError(f"{EXE_NAME} was not found in the release archive")
        if staged.exists():
            _remove_path(staged)
        with bundle.open(members[0]) as source, staged.open("wb") as output:
            shutil.copyfileobj(source, output, 1024 * 1024)
    return staged


def _extract_macos(archive: Path, target: Path, work_dir: Path) -> Path:
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir()
    subprocess.run(["/usr/bin/ditto", "-x", "-k", str(archive), str(extract_dir)], check=True)
    candidates = sorted(p for p in extract_dir.rglob("*.app") if p.is_dir() and p.name == target.name)
    if not candidates:
        raise RuntimeError(f"{target.name} was not found in the release archive")
    staged = target.with_name(target.name + _NEW_SUFFIX)
    if staged.exists():
        _remove_path(staged)
    shutil.move(str(candidates[0]), str(staged))
    subprocess.run(["/usr/bin/xattr", "-dr", "com.apple.quarantine", str(staged)], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return staged


def install_release(release: ReleaseInfo, current_version: str,
                    progress: Optional[Callable[[str, int], None]] = None, timeout: int = 60) -> Path:
    target = _current_target()
    if target is None or not can_self_update():
        raise RuntimeError("Automatic installation is only available for writable packaged builds")
    asset = release_asset_name(release.version)
    if asset is None:
        raise RuntimeError(f"No release package for {platform.system()} {platform.machine()}")
    tag = release.tag or f"v{release.version}"
    base_url = f"{GITHUB_DOWNLOAD_URL}/{quote(tag)}"
    user_agent = f"{APP_NAME}/{current_version}"
    report = progress or (lambda _p, _n: None)
    with tempfile.TemporaryDirectory(prefix="gitcat-update-") as temporary:
        work_dir = Path(temporary)
        checksums_path = work_dir / CHECKSUM_ASSET
        archive_path = work_dir / asset
        report("download", 0)
        _download(f"{base_url}/{CHECKSUM_ASSET}", checksums_path, user_agent, timeout)
        expected = _expected_sha256(checksums_path.read_text(encoding="utf-8", errors="replace"), asset)
        _download(f"{base_url}/{quote(asset)}", archive_path, user_agent, timeout, report)
        report("verify", 100)
        if _sha256(archive_path) != expected:
            raise RuntimeError(f"SHA-256 mismatch for {asset}")
        report("install", 100)
        staged = _extract_windows(archive_path, target) if platform.system() == "Windows" \
            else _extract_macos(archive_path, target, work_dir)
        try:
            _swap_into_place(target, staged)
        except OSError:
            _remove_path(staged)
            raise
    return target


def launch_installed(target: Path, arguments: Optional[list[str]] = None) -> None:
    args = list(sys.argv[1:] if arguments is None else arguments)
    if platform.system() == "Windows":
        env = dict(os.environ)
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen([str(target), *args], cwd=str(target.parent), env=env, creationflags=flags, close_fds=True)
        return
    command = ["/usr/bin/open", "-n", str(target)]
    if args:
        command += ["--args", *args]
    subprocess.Popen(command, close_fds=True)


def cleanup_previous_install(wait_seconds: float = 30.0) -> None:
    target = _current_target()
    if target is None:
        return
    leftovers = [target.with_name(target.name + _OLD_SUFFIX), target.with_name(target.name + _NEW_SUFFIX)]
    deadline = time.monotonic() + wait_seconds
    while True:
        remaining = []
        for path in leftovers:
            if not (path.exists() or path.is_symlink()):
                continue
            try:
                _remove_path(path)
            except OSError:
                remaining.append(path)
        if not remaining or time.monotonic() >= deadline:
            return
        leftovers = remaining
        time.sleep(2)
