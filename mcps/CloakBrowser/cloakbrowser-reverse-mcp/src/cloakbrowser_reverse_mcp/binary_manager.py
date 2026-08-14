from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

import httpx

CHROMIUM_VERSION = "146.0.7680.177.5"
PLATFORM_TAG = "windows-x64"
ARCHIVE_NAME = f"cloakbrowser-{PLATFORM_TAG}.zip"
DOWNLOAD_BASE_URL = "https://cloakbrowser.dev"
GITHUB_API_URL = "https://api.github.com/repos/CloakHQ/cloakbrowser/releases"
GITHUB_DOWNLOAD_BASE_URL = "https://github.com/CloakHQ/cloakbrowser/releases/download"

DOWNLOAD_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)


def browser_root() -> Path:
    override = (os.environ.get("CLOAKBROWSER_BINARY_PATH") or "").strip().strip('"')
    if override:
        return Path(override).resolve().parent
    return Path(__file__).resolve().parents[3]


def binary_path() -> Path:
    override = (os.environ.get("CLOAKBROWSER_BINARY_PATH") or "").strip().strip('"')
    if override:
        return Path(override).resolve()
    return browser_root() / "chrome.exe"


def state_dir(create: bool = True) -> Path:
    path = browser_root() / ".cloakbrowser-reverse"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def downloads_dir() -> Path:
    path = state_dir(create=True) / "downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def version_marker(create: bool = True) -> Path:
    return state_dir(create=create) / "version.json"


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(x) for x in value.split(".") if x.isdigit())


def version_newer(candidate: str, current: str) -> bool:
    return _version_tuple(candidate) > _version_tuple(current)


def installed_version() -> str | None:
    manifest_versions = []
    for item in browser_root().glob("*.manifest"):
        name = item.name.removesuffix(".manifest")
        if name and name[0].isdigit():
            manifest_versions.append(name)
    if manifest_versions:
        return sorted(manifest_versions, key=_version_tuple)[-1]
    marker = version_marker(create=False)
    if marker.exists():
        try:
            return json.loads(marker.read_text(encoding="utf-8")).get("version")
        except Exception:
            return None
    return CHROMIUM_VERSION if binary_path().exists() else None


def binary_info() -> dict:
    root = browser_root()
    version = installed_version()
    return {
        "binary_path": str(binary_path()),
        "browser_root": str(root),
        "installed": binary_path().exists(),
        "installed_version": version,
        "bundled_version": CHROMIUM_VERSION,
        "platform": PLATFORM_TAG,
        "archive_name": ARCHIVE_NAME,
        "state_dir": str(state_dir(create=False)),
        "uses_c_drive_cache": False,
        "update_policy": "in_place_next_to_current_chrome_exe",
    }


def _download_url(version: str) -> str:
    return f"{DOWNLOAD_BASE_URL}/chromium-v{version}/{ARCHIVE_NAME}"


def _github_download_url(version: str) -> str:
    return f"{GITHUB_DOWNLOAD_BASE_URL}/chromium-v{version}/{ARCHIVE_NAME}"


def latest_version() -> str | None:
    resp = httpx.get(GITHUB_API_URL, params={"per_page": 10}, timeout=10.0)
    resp.raise_for_status()
    for release in resp.json():
        tag = release.get("tag_name", "")
        if not tag.startswith("chromium-v") or release.get("draft"):
            continue
        asset_names = {a.get("name") for a in release.get("assets", [])}
        if ARCHIVE_NAME in asset_names:
            return tag.removeprefix("chromium-v")
    return None


def check_for_update() -> dict:
    current = installed_version() or CHROMIUM_VERSION
    try:
        latest = latest_version()
        error = None
    except Exception as exc:
        latest = None
        error = str(exc)
    return {
        "current": current,
        "latest": latest,
        "update_available": bool(latest and version_newer(latest, current)),
        "binary_path": str(binary_path()),
        "error": error,
    }


def _download_file(version: str, dest: Path) -> str:
    urls = [_download_url(version), _github_download_url(version)]
    last_error: Exception | None = None
    for url in urls:
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT) as resp:
                resp.raise_for_status()
                with dest.open("wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                        fh.write(chunk)
            return url
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"download failed for {version}: {last_error}")


def _parse_checksums(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            result[parts[1].lstrip("*")] = parts[0].lower()
    return result


def _fetch_expected_sha256(version: str) -> str | None:
    urls = [
        f"{DOWNLOAD_BASE_URL}/chromium-v{version}/SHA256SUMS",
        f"{GITHUB_DOWNLOAD_BASE_URL}/chromium-v{version}/SHA256SUMS",
    ]
    for url in urls:
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=10.0)
            resp.raise_for_status()
            return _parse_checksums(resp.text).get(ARCHIVE_NAME)
        except Exception:
            continue
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _verify(path: Path, version: str) -> dict:
    expected = _fetch_expected_sha256(version)
    actual = _sha256(path)
    if expected and actual != expected.lower():
        raise RuntimeError(f"checksum mismatch: expected {expected}, got {actual}")
    return {"sha256": actual, "expected": expected, "verified": bool(expected)}


def _safe_extract_zip(archive: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(archive, "r") as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(root)):
                raise RuntimeError(f"archive path traversal: {info.filename}")
        zf.extractall(dest)


def _find_extracted_browser_dir(extract_dir: Path) -> Path:
    matches = list(extract_dir.rglob("chrome.exe"))
    if not matches:
        raise RuntimeError("downloaded archive did not contain chrome.exe")
    # Prefer the shallowest chrome.exe path.
    chrome = sorted(matches, key=lambda p: len(p.parts))[0]
    return chrome.parent


def _copy_tree_contents(src: Path, dest: Path) -> None:
    protected = {"cloakbrowser-reverse-mcp", "profiles", ".cloakbrowser-reverse"}
    for item in src.iterdir():
        if item.name in protected:
            continue
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def download_or_update(version: str | None = None, force: bool = False) -> dict:
    """Download/update the browser binary in-place next to the active chrome.exe.

    No global C: cache is used. Temporary files and extraction staging live
    under <browser_root>\\.cloakbrowser-reverse, where <browser_root> is either
    the folder containing CLOAKBROWSER_BINARY_PATH or this MCP's parent browser
    folder. If users move the whole CloakBrowser folder to E:/F:/..., updates
    stay in that same folder.
    """
    if version:
        target_version = version
    else:
        try:
            target_version = latest_version() or CHROMIUM_VERSION
        except Exception:
            target_version = CHROMIUM_VERSION
    current = installed_version()
    if current and not force and not version_newer(target_version, current):
        return {"status": "already_current", "current": current, "target": target_version, **binary_info()}

    dl_dir = downloads_dir()
    archive = dl_dir / f"chromium-v{target_version}-{ARCHIVE_NAME}"
    source_url = _download_file(target_version, archive)
    checksum = _verify(archive, target_version)
    extract_dir = dl_dir / f"extract-{target_version}"
    _safe_extract_zip(archive, extract_dir)
    src_browser = _find_extracted_browser_dir(extract_dir)
    _copy_tree_contents(src_browser, browser_root())
    version_marker().write_text(json.dumps({"version": target_version, "source_url": source_url}, indent=2), encoding="utf-8")
    return {
        "status": "updated",
        "version": target_version,
        "source_url": source_url,
        "checksum": checksum,
        **binary_info(),
    }
