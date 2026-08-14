# Scoring Model

Use scoring to separate real intelligence from noise. Do not make results look more certain than the evidence supports.

## Evidence Grade

| Grade | Meaning |
| --- | --- |
| A | Exact target or exact parameter match, recent enough, includes code, trace, issue discussion, or packet evidence, and matches the current target shape. |
| B | Same vendor, same app ecosystem, same SDK, same library, or highly similar signing/challenge design. Useful for technique transfer. |
| C | Historical or indirect clue. Useful for names, lineage, old endpoints, and search expansion, but not direct implementation. |
| D | Weak material: reposts, SEO summaries, unverified snippets, thin forum replies, or code without target evidence. |

## Source Priority

| Source Class | Weight | Notes |
| --- | ---: | --- |
| Exact current source code, commit history, live bundle, or official SDK | 10 | Highest value when target match is clear. |
| GitHub/GitLab repo with issues, commits, tests, or packet notes | 9 | Trace forks back to the earliest credible source. |
| Technical forum thread with packet screenshots, call stack, or corrections | 8 | Often stronger than stale code-only repos. |
| Security blog or detailed writeup with derivation | 7 | Prefer original authors over reposts. |
| Package registry with maintained crawler/signing package | 7 | Check release date and issue reports. |
| Developer blog post or tutorial with code | 5 | Useful but commonly stale or copied. |
| Video walkthrough or social thread | 4 | Good for clues; verify elsewhere. |
| Search summary, SEO article, repost, or uncited snippet | 2 | Use mainly for vocabulary expansion. |

## Technical Similarity

Add technical similarity points separately from evidence grade:

- +30 same algorithm or signing construction.
- +25 same JS framework, SDK, or generated client.
- +20 same obfuscator, JSVM style, WASM module family, or challenge vendor.
- +20 same anti-bot vendor or captcha provider.
- +15 same parameter design, timestamp/nonce scheme, or canonical string shape.
- +10 same runtime environment reads such as canvas, WebGL, navigator, storage, or crypto APIs.
- +10 same transport shape such as GraphQL persisted query, protobuf, gRPC-web, or binary envelope.

Cap technical similarity at 60. Similarity raises reference value, not direct reuse certainty.

## Freshness Risk

| Risk | Signals |
| --- | --- |
| Low | Recent code or writeup, active repo, matching endpoint, matching bundle or version, no breakage reports. |
| Medium | Same target but older version, partial endpoint match, forked code, or no current validation. |
| High | Old bundle hash, changed endpoint, closed issues reporting failure, missing dependencies, or vendor flow changed. |

## Final Reference Value

Use this mental formula:

`reference_value = evidence_grade + source_weight + technical_similarity - freshness_risk - reuse_risk`

Report the factors instead of pretending the formula is exact. Mark direct reuse risk as high when code depends on old constants, hardcoded salts, old browser fingerprints, or fragile timing assumptions.

## Confidence Calibration

Report confidence as a number from 0.00 to 1.00 with reasons, not just `high`, `medium`, or `low`.

Example:

```yaml
confidence: 0.82
positive_reasons:
  - exact parameter match
  - current-year source
  - matching JS bundle name
negative_reasons:
  - no live request trace
  - app version unknown
```

Confidence should drop when evidence is stale, copied, missing packet traces, or only same-vendor rather than same-target. Confidence should rise when multiple independent sources agree and current bundle/API fingerprints match.

## Decision Layer

Convert scores into investigation priorities:

| Priority | Use When | Example |
| --- | --- | --- |
| P1 | highest reference value and directly testable now | Analyze `app.123.js` function `generateSign()` first. |
| P2 | strong migration or conflict clue | Compare old MD5 flow with current HMAC-SHA256 evidence. |
| P3 | useful but indirect clue | Inspect WASM only if current bundle still loads the module. |

Each priority must include a reason and a validation step. Do not list more than five priorities unless the user asks for a full backlog.
