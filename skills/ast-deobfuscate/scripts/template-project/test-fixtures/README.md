# Template Project Regression Fixtures

This directory is reserved for small local regression samples used while extending the Decode Action template project.

Keep fixtures small and focused. A fixture should exercise one visitor or one family route, not an entire production bundle.

Recommended fixture classes:

1. `obfuscator-while-switch.js`: order table plus `while(true){switch(...)}`.
2. `obfuscator-dispatcher.js`: simple object dispatcher calls such as `table.add(a, b)`.
3. `sojson-string-call.js`: minimal string array plus decrypt call placeholder.
4. `awsc-expression-shape.js`: ternary, logical expression, sequence expression, and `void` patterns.
5. `state-machine-negative.js`: dynamic state mutation that must not be statically unfolded.

When adding a new visitor:

1. Add or update the smallest fixture that demonstrates the pattern.
2. Run `npm run decode` or `node src/main.js -i <fixture> -o <output>`.
3. Confirm the output still parses.
4. If the fixture is a negative case, confirm the visitor leaves it unchanged or emits a clear residual note.

Do not store large real-world target scripts here. Keep those in the task workspace under `source/original/` or `intermediate/`.
