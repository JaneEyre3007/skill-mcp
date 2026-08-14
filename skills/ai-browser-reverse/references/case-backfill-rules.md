# Case Backfill Rules

Use this file only when the user explicitly asks to backfill a completed Firefox Reverse workflow into the `ai-browser-reverse` skill. Ordinary target artifacts must stay in the current task landing directory and must not be written into this skill directory.

## Preconditions

- The browser reverse task has reached a clear checkpoint: verified signer/cookie/header generation, verified Python replay, or a precise blocker with evidence.
- Important browser evidence is already captured: request id or URL, target fields, script names, hooks/traces used, and verification result.
- Final implementation files, if any, already exist in the task landing directory and pass their available verification command.
- The user explicitly asked to backfill or write the workflow into the skill.

If these are not true, finish the normal reverse task first. Do not backfill unfinished speculation as a reusable case.

## What To Backfill

Prefer process notes over raw artifacts:

- Add or update `references/reverse-process/<category>/<site-slug>-reverse-process.md`.
- Update `references/reverse-process/index.md` with the case name, pattern, and when to read it.
- Add a short pointer in `SKILL.md` only when the lesson affects future task routing, evidence gates, or common false leads.

Only add reusable scripts or frozen assets under this skill when the user explicitly asks for a bundled sanitized case. Otherwise, keep code and raw scripts in the task landing directory.

## Category Selection

Use the smallest matching folder under `references/reverse-process/`:

- `network-hook-signing/`: SDK rewrites XHR/fetch URL, headers, cookie, or body metadata.
- `signatures/`: known function or module returns sign/header/token fields.
- `js-challenges/`: challenge page, two-step cookie, 202/412 flow, or URL suffix challenge.
- `browser-tokens/`: server seed/name/ts or page state becomes a token/cookie.
- `captcha/`: behavior telemetry, trusted input, POW, slider/click verification.

Create a new category only when none of these fits.

## Naming

Use a stable short lowercase slug:

```text
references/reverse-process/<category>/<site-slug>-reverse-process.md
```

Examples:

- `network-hook-signing/douyin-bdms-a-bogus-reverse-process.md`
- `signatures/example-header-sign-reverse-process.md`

Avoid timestamps and local workspace names in case filenames.

## Privacy And Secret Handling

Do not backfill raw secrets into the skill:

- No raw Cookie, Authorization, bearer token, verifier answer, paid account data, private account ID, or full browser fingerprint.
- No full private response JSON, HAR, packet capture, or local session dump.
- Use field names, lengths, masked prefixes, hashes, and provenance instead.
- If the user explicitly requests a private local case with raw evidence, keep it in the task landing directory, not in the installed skill.

## Process Note Shape

Each reverse-process note should include:

- Goal and target contract: page URL class, API URL class, target fields.
- Mode and workspace discipline: delegate/direct-drive choices and landing directory rule.
- Evidence path: Firefox Reverse tools used and what each proved.
- False leads: APIs or functions that looked relevant but were not.
- Implementation path: local runner, env patch, request replay, and file layout.
- Verification traps: things that produce false success, such as HTTP 200 with empty body.
- Claim gates: what can and cannot be claimed from each verification result.

Keep the note actionable. It should teach future runs what to try first and what not to over-claim.

## Landing Directory Rule In Backfilled Cases

Backfilled cases must not teach future runs to create a fixed wrapper directory. State that implementation files go directly under the user-selected landing root:

- If the user provides a folder, write directly into that folder.
- If no folder is provided, choose through the landing directory question in `SKILL.md`.
- Use standard subdirectories such as `collector/`, `analysis/`, `tests/`, `js_reverse_cache/`, `input/`, `output/`, and `logs/` under the selected root.

## Verification Report

When a backfill is finished, report:

- Updated `SKILL.md` section, if any.
- Added or updated reverse-process note path.
- Updated index path.
- Whether raw secrets were excluded.
- What verification result from the original task the case is based on.
