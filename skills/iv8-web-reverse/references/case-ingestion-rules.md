# Case Ingestion Rules

Use this file only when the user explicitly asks to backfill a completed iv8 reproduction into the `iv8-web-reverse` skill case library. Ordinary target scripts must keep downloaded dynamic materials in the current workspace `js_reverse_cache/` and must not write into this skill directory.

Default policy for this user's workflow: keep raw reverse-engineering evidence and generated values unmasked and untruncated. Do not sanitize cookies, headers, tokens, request bodies, response fields, telemetry, or suffixes unless the user explicitly asks for a sanitized/public version.

## Goal

Turn a verified target-specific solution into a small bundled reference case that future iv8 tasks can learn from. The case should document a reusable pattern, not archive a one-off debugging session.

## Preconditions

- A compact target script already exists in the current workspace.
- The script uses iv8 to execute browser-side JavaScript and Python `requests` or `curl_cffi.requests` for real HTTP replay.
- `python -m py_compile` passes for the main script and helper files when helpers exist.
- The iv8-generated cookie, sign, header, token, telemetry, or final URL was verified as non-empty.
- If network conditions allow, the final real request status code was observed and reported.

If these are not true, finish the normal reproduction first. Do not backfill an unverified draft unless the user explicitly asks for a WIP case.

## Category Selection

Choose the smallest matching folder under `references/cases/`:

- `signatures/`: known JS entry returns sign, header, token, or h5st-like fields.
- `js-challenges/`: challenge page, 202/412 flow, page JS cookie, Ruishu-style runtime reproduction, or XHR suffix after challenge.
- `browser-tokens/`: server returns seed/name/ts or similar data and browser JS generates a token/cookie.
- `network-hook-signing/`: SDK hooks XHR/fetch and the useful output is the rewritten URL, headers, cookie, or body metadata from `netLog`.
- `captcha/`: trusted input, behavior collection, TDC, POW, image matching, or telemetry submission.

Only create a new category if none of the existing folders fits.

## Naming

Use a stable, short, lowercase slug:

```text
references/cases/<category>/<site-slug>.py
references/cases/js_reverse_cache/<site-slug>/...
```

Examples:

- `signatures/example-h5st.py`
- `js-challenges/example-202-cookie-url.py`
- `network-hook-signing/example-bdms.py`

Avoid timestamps in case script names. Timestamps are allowed only inside current workspace `js_reverse_cache/` during investigation.

## Optional Sanitization

Only when the user explicitly asks for a sanitized/public case, remove or replace:

- Account cookies, Authorization, bearer tokens, session IDs, CSRF tokens, device IDs tied to the user, and private API keys.
- Phone numbers, ID numbers, email addresses, addresses, order IDs, and exact personal search keywords.
- Large captured responses, private datasets, and response JSON dumps.
- Local absolute paths outside the skill case asset directory.
- Debug dumps that are not required to understand the pattern.
- Temporary comments that mention private accounts, bypass notes, or one-off failures.

Use placeholders such as `YOUR_COOKIE_HERE` only when the user explicitly asks for sanitization or when the case cannot be understood without showing where a user-supplied value belongs.

## Frozen Assets

Keep runtime downloads separate from bundled frozen assets:

- During investigation, write all downloaded or generated material to the current workspace `js_reverse_cache/`.
- During backfill, copy only the minimal reusable JS/HTML/sample files into `references/cases/js_reverse_cache/<site-slug>/`.
- Do not copy run reports, full API responses, HAR files, or bulky packet captures unless the user explicitly asks to preserve them as part of the case.
- If an asset is generated from a live page, name it clearly, for example `challenge.html`, `runtime.js`, `page.html`, or `sdk.js`.

The case script should read bundled assets through `Path(__file__).resolve()` and must not depend on the user's current workspace cache.

## Case Script Shape

Bundled cases may be closer to source examples than generated target scripts, but keep them readable and compact:

- Keep the disclaimer header when the existing cases use it.
- Put editable constants near the top.
- Use `CACHE_DIR = Path.cwd() / "js_reverse_cache"` for runtime outputs if the case writes generated values.
- Use `ASSET_DIR = Path(__file__).resolve().parents[1] / "js_reverse_cache" / "<site-slug>"` for new per-site frozen assets.
- Preserve the exact request serialization needed by the target pattern.
- Add short comments only around non-obvious iv8 lifecycle, patch, event loop, or replay steps.
- Avoid classes, generic frameworks, argparse, and unused helpers.

For historical flat assets, keep their existing paths unless moving them is part of the requested cleanup.

## Documentation Updates

After adding a case, update `references/example-taxonomy.md`:

- Add the script to the folder layout.
- Add a short subsection with source, site, protection type, supporting assets, key iv8 APIs, entry pattern, replay pattern, workflow, and when to use it.
- Add new frozen assets under the JS assets section.
- Update the `Choosing A Case` bullets if the new case represents a distinct reusable pattern.
- Add a matching `*-reverse-process.md` under `references/reverse-process/<category>/` and register it in `references/reverse-process/index.md`.

Update `references/script-writing-rules.md` only when the new case teaches a reusable rule that applies beyond that one site.

## Verification Report

When finished, report:

- Added case script path.
- Added frozen asset directory or files.
- Updated taxonomy sections.
- Whether `py_compile` passed.
- Whether iv8 returned a non-empty cookie/sign/header/token/URL/telemetry.
- Final real HTTP status code if a live request was run.
- Whether the case was kept raw or explicitly sanitized/public.
