# Search Budget

Define the search budget before starting query expansion. The goal is to prevent endless drift while preserving enough room for real OSINT discovery.

## Default Budget

| Scope | Limit |
| --- | ---: |
| Initial broad queries | 20 |
| Initial site/code/package/archive queries | 30 |
| Expansion rounds | 2 normal, 3 difficult |
| High-value nodes per round | 8 |
| Queries per node | 5 |
| Total reviewed results per source class | 10 |
| Total best evidence cards | 8 |

## Expansion Budget

Use one additional round when a result reveals a genuinely new implementation node such as a rare function name, bundle filename, cookie name, vendor marker, package name, algorithm, WASM export, or error string.

Do not spend a round on generic nodes such as `sign`, `token`, `data`, `main.js`, or `index.js` unless combined with an exact target alias.

## Stop Conditions

Stop expanding when any of these conditions apply:

- No new high-value entities appear in the latest round.
- More than 60% of useful-looking results are duplicates, forks, or reposts.
- The latest round produces only weak evidence or unrelated hits.
- New nodes drift away from the primary target type.
- Budget is exceeded.
- The next step is clearly live validation rather than more public search.

## Drift Control

When expansion starts drifting, anchor the next query to at least two of:

- exact domain or brand alias
- exact API path
- exact parameter/header/cookie
- exact bundle or package name
- vendor/protection marker
- target type keyword

If no query can be anchored this way, record the node as background context instead of searching it further.
