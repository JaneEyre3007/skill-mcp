# Firefox Reverse Process Index

Read these notes when a target resembles an existing Firefox Reverse workflow. They are not generic tutorials; each one records evidence gates, false leads, and verification traps from a completed case.

For adding a new case or updating an existing case note, read `../case-backfill-rules.md` first.

| Case | Pattern | Read When |
|---|---|---|
| `network-hook-signing/douyin-bdms-a-bogus-reverse-process.md` | ByteDance/Douyin BDMS rewrites XHR URL with `a_bogus`; Firefox Reverse collects browser evidence, Node补环境 runs BDMS, Python replays request | Target has `/aweme/v1/web/aweme/post/`, `bdms_*.js`, `_SdkGlueInit`, `URLSearchParams.append('a_bogus', ...)`, or mixed `a_bogus` + `x-secsdk-web-signature` |

## Backfill Policy

- Keep long target-specific details in `references/reverse-process/`, not in `SKILL.md`.
- Do not backfill raw Cookie, Authorization, verifier answers, paid account data, or full private response dumps into this skill. Use masked field names, lengths, hashes, and provenance.
- If a case needs reusable code, keep it as a pattern description unless the user explicitly asks to bundle sanitized code assets.
- Always preserve the original workspace path and artifact names in the process note so future runs know where evidence should land, but do not depend on that path existing.
