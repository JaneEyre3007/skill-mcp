#!/usr/bin/env python3
"""Generate public reverse-intelligence search queries from target clues."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse


CHINESE_TERMS = (
    "JS逆向",
    "爬虫逆向",
    "参数加密",
    "签名参数",
    "补环境",
    "反爬",
    "动态cookie",
    "wasm",
)

ENGLISH_TERMS = (
    "reverse engineering",
    "web scraping",
    "signature",
    "request signing",
    "anti bot",
    "token generation",
    "browser environment",
    "wasm",
)

CHINESE_SITES = (
    "52pojie.cn",
    "kanxue.com",
    "xz.aliyun.com",
    "freebuf.com",
    "anquanke.com",
    "blog.csdn.net",
    "cnblogs.com",
    "juejin.cn",
    "zhihu.com",
    "bilibili.com",
    "segmentfault.com",
)

INTERNATIONAL_SITES = (
    "github.com",
    "gist.github.com",
    "gitlab.com",
    "stackoverflow.com",
    "security.stackexchange.com",
    "reddit.com",
    "medium.com",
    "dev.to",
    "habr.com",
    "npmjs.com",
    "pypi.org",
)

TARGET_TYPE_TERMS = {
    "web_api_signature": ("sign", "signature", "timestamp", "nonce", "canonical string", "hash"),
    "encrypted_parameters": ("AES", "RSA", "CryptoJS", "encrypted payload", "decrypt", "payload"),
    "anti_bot_challenge": ("anti bot", "challenge", "sensor", "dynamic cookie", "fingerprint"),
    "captcha": ("captcha", "slider", "GeeTest", "Dingxiang", "Tencent Captcha", "track"),
    "javascript_obfuscation": ("obfuscation", "JSVM", "dispatcher", "string decoder", "webpack"),
    "wasm_crypto": ("wasm", "WebAssembly", "exports", "memory", "crypto"),
    "device_fingerprint": ("fingerprint", "canvas", "WebGL", "navigator", "audio", "timezone"),
    "token_generation": ("token generation", "csrf", "storage", "refresh token", "nonce"),
    "mobile_protocol": ("APK", "package name", "device id", "protobuf", "native SDK"),
    "graphql_api": ("GraphQL", "operationName", "persisted query", "variables", "query hash"),
    "protobuf_api": ("protobuf", "proto", "gRPC-web", "message class", "field number"),
}


@dataclass(frozen=True)
class QueryInput:
    domain: str | None = None
    brands: tuple[str, ...] = ()
    params: tuple[str, ...] = ()
    apis: tuple[str, ...] = ()
    vendors: tuple[str, ...] = ()
    target_type: str | None = None
    profile: str = "all"
    limit: int = 40


def clean_domain(value: str) -> str:
    """Normalize a URL or host into a bare domain."""
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    domain = parsed.netloc.lower()
    if "@" in domain:
        domain = domain.rsplit("@", 1)[1]
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def uniq(items: Iterable[object]) -> list[str]:
    seen = set()
    out: list[str] = []
    for item in items:
        value = " ".join(str(item).split())
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def target_aliases(query_input: QueryInput) -> list[str]:
    aliases: list[str] = []
    if query_input.domain:
        domain = clean_domain(query_input.domain)
        aliases.extend([domain, domain.split(".")[0]])
    aliases.extend(query_input.brands)
    return uniq(aliases)


def selected_sites(profile: str) -> tuple[str, ...]:
    if profile == "cn":
        return CHINESE_SITES
    if profile == "global":
        return INTERNATIONAL_SITES
    return CHINESE_SITES + INTERNATIONAL_SITES


def build_queries(query_input: QueryInput) -> dict[str, list[str]]:
    aliases = target_aliases(query_input)
    params = uniq(query_input.params)
    apis = uniq(query_input.apis)
    vendors = uniq(query_input.vendors)
    type_terms = TARGET_TYPE_TERMS.get(query_input.target_type or "", ())

    broad: list[str] = []
    for param in params:
        broad.extend(
            [
                f'"{param}" "逆向"',
                f'"{param}" "signature"',
                f'"{param}" "function"',
                f'"{param}" "headers"',
            ]
        )
    for api in apis:
        broad.extend([f'"{api}"', f'"{api}" "sign"', f'"{api}" "headers"', f'"{api}" "requests"'])
    for vendor in vendors:
        broad.extend(f'"{vendor}" "{alias}"' for alias in aliases)
    for term in type_terms:
        for alias in aliases:
            broad.append(f'"{alias}" "{term}"')
    for alias in aliases:
        broad.extend(f'"{alias}" "{term}"' for term in CHINESE_TERMS + ENGLISH_TERMS)

    site_queries: list[str] = []
    for site in selected_sites(query_input.profile):
        if site in CHINESE_SITES:
            for alias in aliases:
                site_queries.append(f'site:{site} "{alias}" "逆向"')
            for param in params:
                site_queries.append(f'site:{site} "{param}"')
        else:
            for alias in aliases:
                site_queries.append(f'site:{site} "{alias}" "signature"')
            for param in params:
                site_queries.append(f'site:{site} "{param}" "web scraping"')

    code_queries: list[str] = []
    for alias in aliases:
        code_queries.extend(
            [
                f'"{alias}" "sign" "function"',
                f'"{alias}" "requests"',
                f'"{alias}" language:JavaScript',
                f'"{alias}" path:*.js',
            ]
        )
    for param in params:
        code_queries.extend(
            [
                f'"{param}" "function"',
                f'"{param}" "headers"',
                f'"{param}" "requests"',
                f'"{param}" language:Python',
            ]
        )

    limit = max(query_input.limit, 1)
    return {
        "aliases": aliases,
        "target_type": [query_input.target_type] if query_input.target_type else [],
        "broad": uniq(broad)[:limit],
        "site_queries": uniq(site_queries)[:limit],
        "code_queries": uniq(code_queries)[:limit],
    }


def render_text(result: dict[str, list[str]]) -> str:
    blocks: list[str] = []
    for group, queries in result.items():
        blocks.append(f"[{group}]")
        blocks.extend(queries)
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def render_markdown(result: dict[str, list[str]]) -> str:
    labels = {
        "aliases": "Aliases",
        "target_type": "Target Type",
        "broad": "Broad Queries",
        "site_queries": "Site Queries",
        "code_queries": "Code Queries",
    }
    blocks: list[str] = []
    for group, queries in result.items():
        blocks.append(f"## {labels.get(group, group)}")
        blocks.append("")
        blocks.extend(f"- `{query}`" for query in queries)
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", help="Target domain or URL")
    parser.add_argument("--brand", action="append", help="Brand/app alias; repeatable")
    parser.add_argument("--param", action="append", help="Parameter/header/cookie name; repeatable")
    parser.add_argument("--api", action="append", help="API path or endpoint fragment; repeatable")
    parser.add_argument("--vendor", action="append", help="Protection/vendor clue; repeatable")
    parser.add_argument("--target-type", choices=sorted(TARGET_TYPE_TERMS), help="Primary target classification")
    parser.add_argument("--profile", choices=("all", "cn", "global"), default="all", help="Source profile")
    parser.add_argument("--limit", type=int, default=40, help="Max queries per group")
    parser.add_argument("--format", choices=("json", "text", "markdown"), default="text")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    query_input = QueryInput(
        domain=args.domain,
        brands=tuple(args.brand or ()),
        params=tuple(args.param or ()),
        apis=tuple(args.api or ()),
        vendors=tuple(args.vendor or ()),
        target_type=args.target_type,
        profile=args.profile,
        limit=args.limit,
    )
    result = build_queries(query_input)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(render_markdown(result), end="")
    else:
        print(render_text(result), end="")


if __name__ == "__main__":
    main()
