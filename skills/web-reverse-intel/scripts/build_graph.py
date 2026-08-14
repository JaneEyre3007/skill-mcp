#!/usr/bin/env python3
"""Build a compact Mermaid intelligence graph from extracted entities."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


GROUP_LABELS = {
    "domains": "Domain",
    "endpoints": "API / Endpoint",
    "params": "Parameter / Header / Cookie",
    "files": "Bundle / File",
    "functions": "Function / Export",
    "vendors": "Vendor",
    "algorithms": "Algorithm",
    "fingerprints": "Fingerprint",
    "packages": "Package",
    "errors": "Error / Status",
    "unique_strings": "Unique String",
}


def node_id(prefix: str, index: int) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", prefix)
    return f"{safe}_{index}"


def escape_label(value: str) -> str:
    return value.replace('"', "'")


def normalize_input(data: object) -> dict[str, object]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        merged: dict[str, list[str]] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            entity_type = str(item.get("type", "entities"))
            entity = item.get("entity")
            if entity:
                merged.setdefault(entity_type, []).append(str(entity))
        return merged
    return {}


def build_graph(data: object, target: str = "Target", limit_per_group: int = 8) -> str:
    data = normalize_input(data)
    lines = ["graph TD", f'  Target["{escape_label(target)}"]']
    for group, label in GROUP_LABELS.items():
        values = data.get(group)
        if not isinstance(values, list) or not values:
            continue
        group_id = node_id(group, 0)
        lines.append(f'  {group_id}["{label}"]')
        lines.append(f"  Target --> {group_id}")
        for index, value in enumerate(values[:limit_per_group], start=1):
            item_id = node_id(group, index)
            lines.append(f'  {group_id} --> {item_id}["{escape_label(str(value))}"]')
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes-file", required=True, help="JSON output from extract_entities.py")
    parser.add_argument("--target", default="Target", help="Graph root label")
    parser.add_argument("--limit-per-group", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(Path(args.nodes_file).read_text(encoding="utf-8"))
    print(build_graph(data, args.target, args.limit_per_group), end="")


if __name__ == "__main__":
    main()
