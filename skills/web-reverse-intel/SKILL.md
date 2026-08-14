---
name: web-reverse-intel
description: Pre-reverse OSINT and query-expansion workflow for finding public prior cases, code, writeups, forum threads, package clues, archives, static fingerprints, and entity graph leads before hands-on website/app reverse engineering. Use before deep technical reconstruction such as AST analysis, runtime observation, browser environment analysis, JavaScript runtime emulation, or protocol validation when the target may involve request signing, encrypted parameters, anti-bot challenges, JS/WASM bundles, headers, cookies, tokens, crawler reverse engineering, device fingerprinting, captcha, GraphQL, protobuf, or mobile protocol analysis.
---

# Web Reverse Intel

## Purpose

Use this skill to gather public reverse-engineering intelligence before hands-on analysis. Treat search as an intelligence loop: classify the target, search broadly, extract new nodes, expand queries, score evidence, identify stale material, and produce an actionable brief.

Work only with public materials and user-authorized targets. Do not present third-party code as guaranteed working without validation, and do not help with credential theft, account abuse, payment bypass, or privacy-invasive collection.

## Preflight Rule

Run this skill as a first pass when the user provides a target website, app, API, parameter, protection marker, or JS bundle and has not explicitly asked to skip public research. Spend a bounded search pass before deep technical reconstruction such as AST analysis, runtime observation, browser environment analysis, JavaScript runtime emulation, or protocol validation.

If another reverse-engineering skill is relevant, use this skill first to collect vocabulary, aliases, stale implementations, and vendor clues; then hand off live technical work to the narrower reverse skill.

## Intake

Extract the smallest useful target profile. If the user only gives a website, first derive public aliases and likely search features instead of asking for all missing details.

- Target domain, app name, product name, organization, platform alias, or package identifier.
- API path, JS bundle URL, WASM filename, mobile package name, GraphQL path, or protobuf clue.
- Suspicious parameters, headers, cookies, and globals such as `sign`, `signature`, `token`, `x-s`, `a_bogus`, `h5st`, `m_sign`, `anti-content`, `captcha`, `sensor`, or challenge cookies.
- Error strings, response codes, bundle names, function names, SDK names, vendor clues, or algorithm names.
- Static fingerprints such as JS framework, bundler, npm dependency, obfuscator marker, unique string, source map clue, WASM module, or runtime API read.
- Time scope: latest-only, historical lineage, or broad background.

## Workflow

1. Classify the target type using `references/target-classification.md`; let classification drive source priority, keywords, and ignored rabbit holes.
2. Set a search budget with `references/search-budget.md` before expanding queries.
3. Build aliases from domain, brand names, app names, endpoints, parameters, SDKs, vendors, bundles, fingerprints, and Chinese/English reverse terms.
4. Generate round-one queries with `scripts/build_queries.py`; include the target type when it is known.
5. Search broad sources first, then exact `site:`/quoted/code/package/archive queries using `references/search-sources.md` and `references/query-playbook.md`.
6. Extract intelligence nodes from useful findings: function names, parameters, files, packages, classes, vendors, algorithms, fingerprints, error strings, and unique constants. Use `scripts/extract_entities.py` when working from pasted text or saved snippets.
7. Run a budgeted query expansion loop using `references/query-expansion.md` and `scripts/expand_queries.py`. Repeat only while new high-value nodes appear and budget allows.
8. Score findings with `references/scoring-model.md` and `scripts/score_evidence.py`: evidence grade, source weight, technical similarity, freshness risk, direct reuse risk, and calibrated confidence.
9. Resolve disagreements with `references/conflict-resolution.md`; distinguish true conflict from version migration.
10. Mark stale, deprecated, and negative intelligence using `references/stale-analysis.md` before borrowing old code, salts, constants, or environment assumptions.
11. Build an intelligence graph with `scripts/build_graph.py` when nodes are numerous; use `references/entity-memory.md` for optional long-term memory schema.
12. Produce a final brief using `templates/intelligence-report.md`, `templates/evidence-card.md`, or `templates/graph.md`.

## Source References

Read `references/search-sources.md` when choosing source classes and assigning source priority. It lists domestic and international search surfaces, code sources, archives, forums, blogs, package registries, and coverage notes.

Read `references/query-playbook.md` when constructing first-round queries. Read `references/query-expansion.md` for second-round and later expansion queries. Read `references/search-budget.md` before deciding how far to expand.

Read `references/target-classification.md` when selecting target type, search vocabulary, and likely handoff workflow. Read `references/fingerprint-library.md` when static files, JS snippets, or package names are available.

Read `references/scoring-model.md`, `references/conflict-resolution.md`, and `references/stale-analysis.md` before final ranking. Read `references/entity-memory.md` when the user wants persistent knowledge-base style accumulation.

## Evidence Handling

Do not rank results by source alone. Combine:

- **Directness**: exact target, exact endpoint, exact parameter, exact bundle, or same app family.
- **Source quality**: source code and commit history usually outrank reposted summaries, but packet traces and technical forum posts can outrank stale repos.
- **Technical similarity**: same algorithm, obfuscator, vendor, runtime, parameter design, or fingerprint surface.
- **Freshness**: visible date, commit activity, bundle hash/version match, endpoint continuity, and comments reporting breakage.
- **Reproducibility**: runnable code, trace evidence, issue discussion, test vectors, or step-by-step derivation.
- **Conflict state**: whether newer evidence supersedes old code, or whether findings cover different endpoints, versions, or app variants.
- **Confidence calibration**: numeric confidence plus reasons for and against the conclusion.

Use public findings as leads. Validate against the current target before treating implementation details as current.

## Output Format

Present results as an intelligence brief, not a link dump:

- Target classification and confidence.
- Target aliases, seed features, and query expansion rounds.
- Coverage matrix showing source class, searched status, useful hits, and blind spots.
- Negative intelligence: searched terms/sources that produced no direct hits and the alternatives expanded from them.
- Best evidence cards with grade, source weight, technical similarity, freshness risk, and reuse risk.
- Stale intelligence list explaining why old material may no longer work.
- Intelligence graph as a compact text tree or Mermaid graph connecting target, APIs, parameters, bundles, functions, vendors, algorithms, and prior cases.
- Decision layer: ranked investigation priorities with reasons and live validation probes.

Never claim the search is exhaustive. Say which surfaces were covered and which blind spots remain, such as login-only forums, paid content, deleted repositories, private chats, or region-restricted search results.
