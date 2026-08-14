from __future__ import annotations

import ipaddress
import math
import os
import socket
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlunparse

import httpx

from .binary_manager import state_dir

GEOIP_DB_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"
GEOIP_DB_FILENAME = "GeoLite2-City.mmdb"
GEOIP_UPDATE_INTERVAL = 30 * 86400
DEFAULT_TIMEOUT = 5.0

COUNTRY_LOCALE_MAP = {
    "US": "en-US", "GB": "en-GB", "AU": "en-AU", "CA": "en-CA", "NZ": "en-NZ",
    "DE": "de-DE", "FR": "fr-FR", "ES": "es-ES", "MX": "es-MX", "BR": "pt-BR",
    "IT": "it-IT", "NL": "nl-NL", "JP": "ja-JP", "KR": "ko-KR", "CN": "zh-CN",
    "TW": "zh-TW", "HK": "zh-HK", "RU": "ru-RU", "PL": "pl-PL", "TR": "tr-TR",
    "IN": "hi-IN", "ID": "id-ID", "PH": "en-PH", "TH": "th-TH", "VN": "vi-VN",
}

IP_ECHO_URLS = ["https://api.ipify.org", "https://checkip.amazonaws.com", "https://ifconfig.me/ip"]


def geoip_dir() -> Path:
    path = state_dir() / "geoip"
    path.mkdir(parents=True, exist_ok=True)
    return path


def geoip_db_path() -> Path:
    return geoip_dir() / GEOIP_DB_FILENAME


def _timeout() -> float:
    raw = os.getenv("CLOAKBROWSER_GEOIP_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
        return value if math.isfinite(value) and value >= 0 else DEFAULT_TIMEOUT
    except ValueError:
        return DEFAULT_TIMEOUT


def ensure_proxy_scheme(proxy_url: str) -> str:
    return proxy_url if "://" in proxy_url else f"http://{proxy_url}"


def _assemble_proxy_url(scheme: str, host: str, port: int | None, enc_user: str, enc_pass: str | None, path: str = "", params: str = "", query: str = "", fragment: str = "") -> str:
    if ":" in host:
        host = f"[{host}]"
    userinfo = f"{enc_user}:{enc_pass}@" if enc_pass is not None else (f"{enc_user}@" if enc_user else "")
    netloc = f"{userinfo}{host}"
    if port is not None:
        netloc += f":{port}"
    return urlunparse((scheme, netloc, path, params, query, fragment))


def normalize_proxy_url(url: str) -> str:
    normalized = ensure_proxy_scheme(url)
    try:
        parsed = urlparse(normalized)
        _ = parsed.port
    except ValueError:
        return normalized
    if parsed.username is None and parsed.password is None:
        return normalized
    raw_user = parsed.username or ""
    enc_user = quote(unquote(raw_user), safe="") if raw_user else ""
    if parsed.password is not None:
        raw_pass = parsed.password
        enc_pass = quote(unquote(raw_pass), safe="") if raw_pass else ""
    else:
        enc_pass = None
    return _assemble_proxy_url(parsed.scheme, parsed.hostname or "", parsed.port, enc_user, enc_pass, parsed.path, parsed.params, parsed.query, parsed.fragment)


def is_socks_proxy(proxy: str | None) -> bool:
    return bool(proxy and proxy.lower().startswith(("socks5://", "socks5h://")))


def _download_geoip_db(path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    with httpx.stream("GET", GEOIP_DB_URL, follow_redirects=True, timeout=60.0) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                fh.write(chunk)
    tmp.replace(path)


def ensure_geoip_db() -> Path | None:
    path = geoip_db_path()
    if path.exists():
        try:
            if time.time() - path.stat().st_mtime > GEOIP_UPDATE_INTERVAL:
                _download_geoip_db(path)
        except Exception:
            pass
        return path
    try:
        _download_geoip_db(path)
        return path
    except Exception:
        return None


def resolve_proxy_ip(proxy_url: str) -> str | None:
    try:
        host = urlparse(proxy_url).hostname
        if not host:
            return None
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            pass
        infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return infos[0][4][0] if infos else None
    except Exception:
        return None


def resolve_exit_ip(proxy_url: str, timeout: float | None = None) -> str | None:
    deadline = time.monotonic() + (timeout if timeout is not None else _timeout())
    for url in IP_ECHO_URLS:
        remaining = max(deadline - time.monotonic(), 0.1)
        try:
            resp = httpx.get(url, proxy=proxy_url, timeout=min(10.0, remaining))
            resp.raise_for_status()
            ip = resp.text.strip()
            ipaddress.ip_address(ip)
            return ip
        except Exception:
            continue
    return None


def resolve_proxy_geo_with_ip(proxy_url: str) -> tuple[str | None, str | None, str | None]:
    try:
        import geoip2.database
    except ImportError:
        raise ImportError("geoip2 is required for geoip=True. Install: pip install geoip2") from None

    proxy_url = normalize_proxy_url(proxy_url)
    db = ensure_geoip_db()
    if db is None:
        return None, None, None
    ip = resolve_exit_ip(proxy_url, timeout=_timeout()) or resolve_proxy_ip(proxy_url)
    if not ip:
        return None, None, None
    try:
        with geoip2.database.Reader(str(db)) as reader:
            resp = reader.city(ip)
            timezone = resp.location.time_zone
            country = resp.country.iso_code
            locale = COUNTRY_LOCALE_MAP.get(country) if country else None
            return timezone, locale, ip
    except Exception:
        return None, None, ip
