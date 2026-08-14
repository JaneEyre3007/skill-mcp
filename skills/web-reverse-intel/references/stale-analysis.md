# Stale Intelligence Analysis

Old reverse-engineering material can still be valuable, but only after its failure modes are named.

## Stale Signals

- Bundle hash, chunk filename, source map, or app version no longer exists.
- Endpoint path changed or response shape no longer matches.
- Parameter was removed, renamed, moved to headers, or split across multiple values.
- Timestamp, nonce, salt, IV, key derivation, or canonical string changed.
- Cookie/challenge flow changed vendor version or added browser fingerprint fields.
- Repository issues report that the code no longer works.
- Public code hardcodes device IDs, user agents, cookies, salts, or test tokens.
- Required runtime APIs are missing from the current target or were replaced by WASM/native code.

## How To Use Historical Findings

- Keep old function names, parameters, bundle names, constants, and error strings as search expansion nodes.
- Use old call chains to guide live breakpoints, not to skip validation.
- Compare old and current request shapes before porting code.
- Treat old working scripts as historical evidence unless they include recent commits or current issue confirmations.

## Deprecated Intelligence Output

For each historical case, record:

- What it claimed to solve.
- Which target/version/date it appears to cover.
- Why it may be stale.
- Which clues remain useful.
- What live check would confirm or reject it.

## Common Live Checks

- Search current bundles for the same parameter, function, constant, or vendor marker.
- Compare endpoint path, method, headers, body fields, and response code.
- Check whether old repo issues mention breakage or updated forks.
- Verify whether the old vendor marker appears in current traffic or HTML.
- Confirm whether the algorithm still receives the same input fields.

## Negative Intelligence

Record no-hit and low-hit searches. This prevents repeated dead-end searches and helps justify later expansion to same-vendor, same-SDK, same-algorithm, or same-ecosystem cases.

For each no-hit area, record:

- searched terms
- searched source classes
- date or search round
- why the result was considered no-hit
- expanded alternative chosen next

Example:

```yaml
no_direct_case:
  searched_terms:
    - "example.com" "JS逆向"
    - "example.com" "signature"
  searched_sources:
    - general_search
    - github_code
  result: no direct public reverse case found
  expanded_alternatives:
    - same Akamai cookie family
    - same `x-token` parameter design
```

Negative intelligence is not failure. It is coverage evidence and a reason to pivot deliberately.
