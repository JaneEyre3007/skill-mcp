# Query Expansion

Search is recursive. Do not stop after the first result set if useful findings reveal new names, files, strings, or vendor clues.

## Expansion Nodes

Extract these nodes from useful findings:

- Function names: `getSign`, `generateBogus`, `encryptParams`, decoder names, webpack export names.
- Parameters, headers, cookies, and storage keys.
- JS/WASM filenames, chunk names, source map names, APK/IPA package names, npm/PyPI package names.
- Vendor markers, challenge paths, global variables, SDK names, class names, and protobuf/GraphQL operation names.
- Algorithm names, constants, salts, IV labels, error messages, response codes, and unique strings.

## Loop

1. Start with round-one queries from target aliases and known parameters.
2. For each useful result, extract nodes and tag their type.
3. Generate expansion queries from each high-value node.
4. Search exact quoted strings first, then source-specific `site:` and code-search variants.
5. Add newly discovered nodes to the graph and continue.
6. Stop when no new high-value nodes appear, results repeat, source quality drops, or the time/search budget is reached.

## High-Value Node Rules

Prioritize nodes that are unique, implementation-shaped, and searchable:

- Good: exact function names, rare cookies, bundle filenames, endpoint fragments, package names, stack traces, vendor globals.
- Medium: common parameters plus a target alias, common algorithm names plus a bundle or vendor.
- Weak: generic words such as `sign`, `token`, `data`, `main.js`, or `index.js` without target context.

## Expansion Query Patterns

- `"{node}" "{target_alias}"`
- `"{node}" "逆向"`
- `"{node}" "signature"`
- `"{node}" "web scraping"`
- `"{node}" "function"`
- `"{node}" "headers"`
- `site:github.com "{node}" "{target_alias}"`
- `site:52pojie.cn "{node}"`
- `site:kanxue.com "{node}"`
- `site:blog.csdn.net "{node}" "JS逆向"`
- `site:npmjs.com "{node}"` or `site:pypi.org "{node}"` for package-like nodes.

## Round Budget

Default to two search rounds for normal work and three rounds for difficult targets. More rounds are useful only when each round produces new high-quality nodes.
