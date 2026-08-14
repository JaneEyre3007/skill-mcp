import { describe, expect, it } from "vitest";
import { redact } from "../src/logging.js";

describe("redact", () => {
  it("redacts sk-style and JSON string secret values", () => {
    const secret = "A".repeat(44);
    const out = redact(JSON.stringify({ apiKey: secret, openai: "sk-" + "b".repeat(20) }));

    expect(out).toContain('"apiKey":"***REDACTED_LONG_SECRET***"');
    expect(out).toContain('"openai":"sk-***REDACTED***"');
    expect(out).not.toContain(secret);
  });

  it("does not redact long path segments outside JSON string values", () => {
    const path = "D:/cache/" + "a".repeat(44) + "/bundle.js";

    expect(redact(path)).toBe(path);
  });
});
