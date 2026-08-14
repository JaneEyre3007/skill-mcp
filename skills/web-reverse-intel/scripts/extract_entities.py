#!/usr/bin/env python3
"""Extract searchable intelligence nodes from reverse-engineering text snippets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


GENERIC_WORDS = {
    "data",
    "main",
    "index",
    "token",
    "sign",
    "true",
    "false",
    "null",
    "this",
    "return",
    "function",
    "headers",
    "catch",
    "then",
    "forEach",
    "reduce",
    "filter",
    "map",
    "pop",
    "push",
}

VENDOR_PATTERNS = {
    "akamai": r"\bakamai\b|\babck\b|\bbm_sz\b",
    "cloudflare": r"\bcloudflare\b|\bcf_clearance\b|\bturnstile\b",
    "ruishu": r"瑞数|\bruishu\b|\brivers\b|\b_?ts\b|\br2mKa\b",
    "geetest": r"极验|\bgeetest\b|\bgt\b|\bchallenge\b",
    "dingxiang": r"顶象|\bdingxiang\b",
    "tencent-captcha": r"腾讯验证码|\btcaptcha\b|\bcaptcha\.qq\.com\b",
    "aliyun": r"阿里云|\baliyun\b|\baliyuncs\b",
}

ALGORITHM_PATTERNS = (
    "AES",
    "RSA",
    "DES",
    "3DES",
    "HMAC",
    "MD5",
    "SHA1",
    "SHA-1",
    "SHA256",
    "SHA-256",
    "SHA512",
    "SHA-512",
    "Base64",
    "CryptoJS",
    "protobuf",
    "GraphQL",
    "WASM",
    "WebAssembly",
)

ALGORITHM_WORDS = {item.lower().replace("-", "") for item in ALGORITHM_PATTERNS}
FILE_SUFFIXES = (".js", ".mjs", ".wasm", ".map", ".apk", ".ipa", ".proto", ".json")
NON_DOMAIN_SUFFIXES = {"push", "call", "apply", "then", "catch", "map", "forEach", "filter", "reduce"}
ENDPOINT_PREFIXES = ("api/", "gw/", "graphql/", "v1/", "v2/", "h5/", "ajax/", "rest/", "rpc/", "openapi/")

FINGERPRINT_PATTERNS = {
    "webpackJsonp": r"\bwebpackJsonp\b",
    "__webpack_require__": r"__webpack_require__",
    "__NEXT_DATA__": r"__NEXT_DATA__",
    "vite": r"\b__vite|\bVite\b",
    "CryptoJS": r"\bCryptoJS\b|crypto-js",
    "JSEncrypt": r"\bJSEncrypt\b",
    "WebAssembly": r"WebAssembly\.(?:instantiate|compile)|\.wasm\b",
    "sourceMappingURL": r"sourceMappingURL",
    "obfuscator.io": r"obfuscator\.io|javascript-obfuscator",
    "sojson": r"sojson|sojson\.v",
    "jsjiami": r"jsjiami|\u52a0\u5bc6",
    "canvas_fingerprint": r"canvas|getImageData|toDataURL",
    "webgl_fingerprint": r"WebGLRenderingContext|getParameter\(",
    "audio_fingerprint": r"AudioContext|OfflineAudioContext",
    "navigator_fingerprint": r"navigator\.(?:webdriver|plugins|languages|hardwareConcurrency|deviceMemory)",
}


def uniq(items: Iterable[object]) -> list[str]:
    seen = set()
    out: list[str] = []
    for item in items:
        value = " ".join(str(item).strip().split())
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def normalize_domain(value: str) -> str:
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def keep_identifier(value: str) -> bool:
    lowered = value.lower()
    normalized = lowered.replace("-", "")
    if lowered in GENERIC_WORDS or normalized in ALGORITHM_WORDS:
        return False
    if len(value) < 4:
        return False
    return bool(re.search(r"[A-Za-z_]", value))


def keep_domain(value: str) -> bool:
    lowered = value.lower()
    suffix = lowered.rsplit(".", 1)[-1]
    return not lowered.endswith(FILE_SUFFIXES) and suffix not in NON_DOMAIN_SUFFIXES


def keep_package(value: str) -> bool:
    lowered = value.lower()
    return not lowered.startswith(ENDPOINT_PREFIXES)


def extract_entities(text: str) -> dict[str, list[str]]:
    urls = re.findall(r"https?://[^\s'\"<>]+", text)
    domains = [normalize_domain(url) for url in urls]
    domains.extend(re.findall(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", text, flags=re.I))

    endpoints = re.findall(r"(?<!:)\/(?:api|gw|graphql|v\d|h5|ajax|rest|rpc|openapi)\/[A-Za-z0-9_./?=&%-]*", text)
    files = re.findall(r"\b[A-Za-z0-9_.-]+\.(?:js|mjs|wasm|map|apk|ipa|proto|json)\b", text, flags=re.I)

    functions = []
    functions.extend(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]{3,})\s*\(", text))
    functions.extend(re.findall(r"\b([A-Za-z_$][\w$]{3,})\s*[:=]\s*(?:async\s+)?function\b", text))
    functions.extend(re.findall(r"\b([A-Za-z_$][\w$]{3,})\s*[:=]\s*(?:async\s*)?\([^)]*\)\s*=>", text))
    functions.extend(re.findall(r"\.([A-Za-z_$][\w$]{3,})\s*\(", text))

    params = []
    params.extend(re.findall(r"[?&]([A-Za-z_][\w$-]{2,})=", text))
    params.extend(re.findall(r"['\"]([A-Za-z_][\w$-]{2,})['\"]\s*:", text))
    params.extend(re.findall(r"\b([A-Za-z_][\w$-]*(?:sign|token|nonce|timestamp|captcha|sensor|fp|bogus|cookie|secret)[\w$-]*)\b", text, flags=re.I))

    packages = re.findall(r"\b(?:com\.[A-Za-z0-9_.]+|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|@[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b", text)
    errors = re.findall(r"\b(?:HTTP\s*)?(?:401|403|412|429|503)\b|[A-Za-z0-9_.-]*(?:Error|Exception|Denied|Forbidden)[A-Za-z0-9_.-]*", text)

    vendors = []
    for vendor, pattern in VENDOR_PATTERNS.items():
        if re.search(pattern, text, flags=re.I):
            vendors.append(vendor)

    fingerprints = []
    for fingerprint, pattern in FINGERPRINT_PATTERNS.items():
        if re.search(pattern, text, flags=re.I):
            fingerprints.append(fingerprint)

    algorithms = []
    for algorithm in ALGORITHM_PATTERNS:
        if re.search(r"\b" + re.escape(algorithm) + r"\b", text, flags=re.I):
            algorithms.append(algorithm)

    unique_strings = []
    for quoted in re.findall(r"['\"]([^'\"]{8,80})['\"]", text):
        if re.search(r"[/_.:-]", quoted) and not quoted.startswith(("http://", "https://")):
            unique_strings.append(quoted)

    function_nodes = uniq(item for item in functions if keep_identifier(item))
    function_lookup = {item.lower() for item in function_nodes}

    return {
        "domains": uniq(domain for domain in (normalize_domain(domain) for domain in domains) if keep_domain(domain)),
        "endpoints": uniq(endpoints),
        "files": uniq(files),
        "functions": function_nodes,
        "params": uniq(item for item in params if keep_identifier(item) and item.lower() not in function_lookup),
        "packages": uniq(item for item in packages if keep_package(item)),
        "vendors": uniq(vendors),
        "algorithms": uniq(algorithms),
        "fingerprints": uniq(fingerprints),
        "errors": uniq(errors),
        "unique_strings": uniq(unique_strings),
    }


def render_markdown(result: dict[str, list[str]]) -> str:
    blocks: list[str] = []
    for group, values in result.items():
        blocks.append("## " + group.replace("_", " ").title())
        blocks.append("")
        if values:
            blocks.extend(f"- `{value}`" for value in values)
        else:
            blocks.append("- none")
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def read_input(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", help="Text snippet to analyze")
    parser.add_argument("--file", help="UTF-8 file to analyze")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = extract_entities(read_input(args))
    if args.format == "markdown":
        print(render_markdown(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
