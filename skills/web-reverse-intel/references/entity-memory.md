# Entity Memory

Use entity memory only when the user wants long-term accumulation across tasks. The skill includes seed JSON files under `memory/` as schemas. For live projects, copy them into the current workspace or a user-approved knowledge-base location before writing updates.

Do not write private targets, secrets, cookies, tokens, credentials, or proprietary code into public repository memory files.

## Entity Shape

```json
{
  "entity": "CryptoJS AES",
  "type": "algorithm",
  "seen_in": ["siteA", "siteB"],
  "related_cases": ["github/project1"],
  "related_entities": ["JSEncrypt", "sign"],
  "confidence": 0.72,
  "last_seen": "2026-08-12",
  "notes": "Useful for search expansion, not proof of direct reuse."
}
```

## Memory Types

- `entities.json`: generic nodes such as functions, files, parameters, bundles, packages, and unique strings.
- `algorithms.json`: algorithms, crypto libraries, canonicalization patterns, and protocol shapes.
- `vendors.json`: anti-bot/captcha/vendor markers and challenge families.
- `signatures.json`: signing parameter designs, canonical string patterns, timestamp/nonce schemes.
- `cases/`: optional per-target case files when the user explicitly wants a persistent case library.

## Update Rules

Add memory only after evidence is scored. Store source links and confidence reasons, not just names.

Merge by normalized entity name and type. Append new `seen_in` and `related_cases` instead of duplicating records.

Mark stale entries rather than deleting them; old names are often useful expansion nodes.
