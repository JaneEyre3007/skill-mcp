# Conflict Resolution

Public reverse-engineering findings often disagree because targets change versions, endpoints, app channels, or protection vendors. Treat disagreement as evidence to analyze, not as an immediate contradiction.

## When Findings Disagree

Compare:

- publication date and commit date
- target domain, endpoint, and HTTP method
- app version, bundle hash, source map, package version, or release channel
- parameter names, header names, cookie names, and body shape
- algorithm, canonical string, salt, key derivation, and runtime dependencies
- issue comments or replies reporting breakage or fixes
- whether the finding has packet traces, live code, or only copied snippets

## Preference Rules

Prefer newer verified traces over older complete code when the target shape matches.

Prefer current endpoint/bundle evidence over generic same-vendor articles.

Prefer original posts, commits, or issue discussions over reposts.

Prefer evidence that explains inputs and derivation over code that only returns a hardcoded result.

Keep older material when it explains naming, migration history, or why a prior approach stopped working.

## Output

For each conflict, report:

- conflicting claims
- likely explanation: version migration, endpoint split, app variant, vendor change, or weak evidence
- preferred current lead
- historical clue still worth keeping
- live validation step that would settle the conflict
