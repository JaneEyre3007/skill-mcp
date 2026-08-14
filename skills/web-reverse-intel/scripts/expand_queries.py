#!/usr/bin/env python3
"""Generate second-round search queries from extracted intelligence nodes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


GENERIC_NODES = {
    "sign",
    "token",
    "data",
    "main.js",
    "index.js",
    "api",
    "function",
    "headers",
}

SITE_TEMPLATES = (
    'site:github.com "{node}" "{alias}"',
    'site:gist.github.com "{node}"',
    'site:gitlab.com "{node}" "{alias}"',
    'site:52pojie.cn "{node}"',
    'site:kanxue.com "{node}"',
    'site:blog.csdn.net "{node}" "JS逆向"',
    'site:cnblogs.com "{node}" "爬虫逆向"',
    'site:juejin.cn "{node}" "逆向"',
    'site:npmjs.com "{node}"',
    'site:pypi.org "{node}"',
)


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


def flatten_nodes(data: dict[str, object]) -> list[str]:
    nodes: list[str] = []
    for key, value in data.items():
        if key == "aliases":
            continue
        if isinstance(value, list):
            nodes.extend(str(item) for item in value)
        elif isinstance(value, str):
            nodes.append(value)
    return uniq(nodes)


def is_high_value(node: str) -> bool:
    lowered = node.lower()
    if lowered in GENERIC_NODES:
        return False
    if len(node) < 4:
        return False
    if "/" in node or "." in node or "_" in node or "-" in node:
        return True
    if any(char.isdigit() for char in node):
        return True
    return len(node) >= 7


def build_expansion_queries(nodes: list[str], aliases: list[str], limit: int) -> dict[str, list[str]]:
    useful_nodes = [node for node in uniq(nodes) if is_high_value(node)]
    aliases = uniq(aliases)
    primary_alias = aliases[0] if aliases else ""

    exact: list[str] = []
    reverse_terms: list[str] = []
    site_queries: list[str] = []
    code_queries: list[str] = []

    for node in useful_nodes:
        exact.append(f'"{node}"')
        if primary_alias:
            exact.append(f'"{node}" "{primary_alias}"')
        reverse_terms.extend(
            [
                f'"{node}" "逆向"',
                f'"{node}" "signature"',
                f'"{node}" "web scraping"',
                f'"{node}" "function"',
                f'"{node}" "headers"',
            ]
        )
        for template in SITE_TEMPLATES:
            site_queries.append(template.format(node=node, alias=primary_alias or node))
        code_queries.extend(
            [
                f'"{node}" language:JavaScript',
                f'"{node}" language:Python',
                f'"{node}" "requests"',
                f'"{node}" "fetch"',
            ]
        )

    limit = max(limit, 1)
    return {
        "nodes": useful_nodes[:limit],
        "exact_queries": uniq(exact)[:limit],
        "reverse_queries": uniq(reverse_terms)[:limit],
        "site_queries": uniq(site_queries)[:limit],
        "code_queries": uniq(code_queries)[:limit],
    }


def render_markdown(result: dict[str, list[str]]) -> str:
    labels = {
        "nodes": "Expansion Nodes",
        "exact_queries": "Exact Queries",
        "reverse_queries": "Reverse Queries",
        "site_queries": "Site Queries",
        "code_queries": "Code Queries",
    }
    blocks: list[str] = []
    for key, values in result.items():
        blocks.append(f"## {labels.get(key, key)}")
        blocks.append("")
        blocks.extend(f"- `{value}`" for value in values)
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def parse_nodes_file(path: str) -> tuple[list[str], list[str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    aliases = []
    for key in ("domains", "aliases"):
        value = data.get(key)
        if isinstance(value, list):
            aliases.extend(str(item) for item in value)
    return flatten_nodes(data), uniq(aliases)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", action="append", help="Expansion node; repeatable")
    parser.add_argument("--alias", action="append", help="Target alias/domain/brand; repeatable")
    parser.add_argument("--nodes-file", help="JSON output from extract_entities.py")
    parser.add_argument("--limit", type=int, default=40, help="Max queries per group")
    parser.add_argument("--format", choices=("json", "markdown", "text"), default="json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nodes = list(args.node or ())
    aliases = list(args.alias or ())
    if args.nodes_file:
        file_nodes, file_aliases = parse_nodes_file(args.nodes_file)
        nodes.extend(file_nodes)
        aliases.extend(file_aliases)

    result = build_expansion_queries(nodes, aliases, args.limit)
    if args.format == "markdown":
        print(render_markdown(result), end="")
    elif args.format == "text":
        for values in result.values():
            for value in values:
                print(value)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
